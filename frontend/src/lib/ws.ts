/**
 * WebSocket manager — GovFlow real-time events.
 *
 * Security hardening (Wave 0, task 0.7):
 *   - Token is NEVER placed in the URL query string (would leak into server
 *     access logs, browser history, and Referer headers).
 *   - Instead: connect without credentials, then send an auth frame as the
 *     very first message after onopen.  The backend accepts the token within
 *     5 seconds or closes the socket with code 1008 (Policy Violation).
 *   - On auth rejection ({type:"auth", ok:false} or close code 1008), the
 *     manager calls the optional `onAuthFailure` callback so the caller can
 *     redirect to the login page.
 *   - Exponential backoff reconnect; auth frame is re-sent on every reconnect.
 */

import type { WSMessage } from "@/lib/types";

type MessageHandler = (msg: WSMessage) => void;

/** Callback invoked when the server explicitly rejects the auth token. */
type AuthFailureHandler = () => void;

// Warn once if the env var is missing — do not spam the console.
let _warnedMissingUrl = false;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private listeners = new Map<string, Set<MessageHandler>>();
  private pendingSubscriptions = new Set<string>();

  /** Optional callback for auth rejection (1008 close or {type:"auth",ok:false}). */
  private onAuthFailure: AuthFailureHandler | null = null;

  /** Register a handler called when the server rejects the token. */
  setAuthFailureHandler(handler: AuthFailureHandler): void {
    this.onAuthFailure = handler;
  }

  connect(token: string): void {
    // If already connected OR connecting with the same token, no-op.
    const currentState = this.ws?.readyState;
    if (currentState === WebSocket.OPEN || currentState === WebSocket.CONNECTING) {
      if (this._currentToken === token) return;
      // Different token (e.g. token refresh) — swap connection cleanly.
      this._intentionalClose = true;
      try {
        if (this.ws) {
          // Detach handlers on the old socket so stale events don't fire.
          this.ws.onopen = null;
          this.ws.onmessage = null;
          this.ws.onerror = null;
          this.ws.onclose = null;
          this.ws.close();
        }
      } catch {
        /* noop */
      }
      this.ws = null;
    }
    this._currentToken = token;
    this._intentionalClose = false;

    // --- URL construction (NO token in URL) ---
    if (!process.env.NEXT_PUBLIC_WS_URL && !_warnedMissingUrl) {
      console.warn(
        "[WS] NEXT_PUBLIC_WS_URL is not set. " +
        "Falling back to localhost:8100 in development or same-host in production. " +
        "Set NEXT_PUBLIC_WS_URL in .env.local to silence this warning.",
      );
      _warnedMissingUrl = true;
    }

    const baseUrl =
      process.env.NEXT_PUBLIC_WS_URL ??
      (typeof window !== "undefined" && window.location.hostname === "localhost"
        ? "ws://localhost:8100/api/ws"
        : null);

    // Never append ?token= — token travels in the first message frame only.
    const url = baseUrl
      ? baseUrl
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      this.reconnectAttempts = 0;

      // Send auth frame immediately — backend expects this within 5 seconds.
      // An empty token means anonymous access (public:* topics only).
      if (token) {
        this._sendRaw({ action: "auth", token });
      }

      // Re-subscribe to any topics that were registered before the connection
      // was established (or after a previous disconnect).
      this.pendingSubscriptions.forEach((topic) => {
        this._sendSubscribeAction("subscribe", topic);
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data as string) as Record<string, unknown>;

        // --- Auth response from server ---
        if (raw.type === "auth") {
          if (raw.ok === false) {
            console.warn("[WS] Auth rejected by server — triggering re-auth.");
            this._triggerAuthFailure();
          }
          // ok:true is a silent ack; no further processing needed.
          return;
        }

        // Ack messages (subscribe/unsubscribe confirmation).
        if (raw.ack) return;

        // Server-reported errors.
        if (raw.error) {
          console.error("[WS] Server error:", raw.error);
          return;
        }

        const msg: WSMessage = {
          topic: (raw.topic as string) ?? "",
          event: (raw.event as string) ?? "",
          data: raw.data ?? raw,
        };
        // Fire topic-specific handlers.
        this.listeners.get(msg.topic)?.forEach((h) => h(msg));
        // Fire wildcard handlers.
        this.listeners.get("*")?.forEach((h) => h(msg));
      } catch (e) {
        console.error("[WS] Parse error:", e);
      }
    };

    this.ws.onclose = (event) => {
      if (this._intentionalClose) {
        this._intentionalClose = false;
        return;
      }

      // 1008 = Policy Violation — server rejected the token.
      if (event.code === 1008) {
        console.warn("[WS] Connection closed with 1008 (Policy Violation) — auth failure.");
        this._triggerAuthFailure();
        return; // Do NOT reconnect after auth rejection.
      }

      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30_000);
        setTimeout(() => this.connect(token), delay);
      }
    };

    this.ws.onerror = () => {
      // Silenced — onclose handles reconnection + auth failures.
      // Logging the Event object triggers the Next.js dev error overlay.
    };
  }

  subscribe(topic: string, handler: MessageHandler): () => void {
    if (!this.listeners.has(topic)) this.listeners.set(topic, new Set());
    this.listeners.get(topic)!.add(handler);

    if (topic !== "*") {
      this.pendingSubscriptions.add(topic);
      // Only send subscribe on anonymous sockets for public topics.
      const isPublic = topic.startsWith("public:");
      if (isPublic || this._currentToken) {
        this._sendSubscribeAction("subscribe", topic);
      }
    }

    return () => {
      this.listeners.get(topic)?.delete(handler);
      if (this.listeners.get(topic)?.size === 0) {
        this.listeners.delete(topic);
        if (topic !== "*") {
          this.pendingSubscriptions.delete(topic);
          this._sendSubscribeAction("unsubscribe", topic);
        }
      }
    };
  }

  getState(): "connected" | "connecting" | "disconnected" {
    if (!this.ws) return "disconnected";
    switch (this.ws.readyState) {
      case WebSocket.OPEN:
        return "connected";
      case WebSocket.CONNECTING:
        return "connecting";
      default:
        return "disconnected";
    }
  }

  disconnect(): void {
    this._intentionalClose = true;
    this.ws?.close();
    this.ws = null;
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /** Send a raw JSON message if the socket is open. */
  private _sendRaw(payload: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  /** Send subscribe / unsubscribe, honouring anonymous socket restrictions. */
  private _sendSubscribeAction(action: "subscribe" | "unsubscribe", topic: string): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    // Do not send non-public subscriptions on an anonymous (no-token) socket.
    if (!this._currentToken && !topic.startsWith("public:")) return;
    this._sendRaw({ action, topic });
  }

  /** Fire the registered auth-failure handler and close the socket. */
  private _triggerAuthFailure(): void {
    this.disconnect();
    this.onAuthFailure?.();
  }

  private _intentionalClose = false;
  private _currentToken: string | null = null;
}

export const wsManager = new WebSocketManager();

// ---------------------------------------------------------------------------
// Global auth:expired listener — close the WS connection whenever the API
// layer detects a 401 so the socket doesn't linger with a stale token.
// ---------------------------------------------------------------------------
if (typeof window !== "undefined") {
  window.addEventListener("auth:expired", () => {
    wsManager.disconnect();
  });
}
