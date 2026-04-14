import type { WSMessage } from "@/lib/types";

type MessageHandler = (msg: WSMessage) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private listeners = new Map<string, Set<MessageHandler>>();
  private pendingSubscriptions = new Set<string>();

  connect(token: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this._intentionalClose = false;

    // In dev, Next.js rewrites don't proxy WebSocket — connect to backend directly
    const backendHost =
      process.env.NEXT_PUBLIC_WS_URL ??
      (typeof window !== "undefined" && window.location.hostname === "localhost"
        ? "ws://localhost:8100/api/ws"
        : null);

    const url = backendHost
      ? `${backendHost}?token=${token}`
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws?token=${token}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      this.reconnectAttempts = 0;
      // Re-subscribe to any pending topics
      this.pendingSubscriptions.forEach((topic) => {
        this.sendAction("subscribe", topic);
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        // Handle ack messages
        if (raw.ack) return;
        // Handle error messages
        if (raw.error) {
          console.error("[WS] Server error:", raw.error);
          return;
        }
        const msg: WSMessage = {
          topic: raw.topic ?? "",
          event: raw.event ?? "",
          data: raw.data ?? raw,
        };
        // Fire handlers for specific topic
        this.listeners.get(msg.topic)?.forEach((h) => h(msg));
        // Fire wildcard handlers
        this.listeners.get("*")?.forEach((h) => h(msg));
      } catch (e) {
        console.error("[WS] Parse error:", e);
      }
    };

    this.ws.onclose = () => {
      if (this._intentionalClose) {
        this._intentionalClose = false;
        return;
      }
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
        setTimeout(() => this.connect(token), delay);
      }
    };

    this.ws.onerror = () => {
      // Silenced — onclose handles reconnection. Logging the Event object
      // triggers the Next.js dev error overlay unnecessarily.
    };
  }

  subscribe(topic: string, handler: MessageHandler): () => void {
    if (!this.listeners.has(topic)) this.listeners.set(topic, new Set());
    this.listeners.get(topic)!.add(handler);

    // Track subscription for reconnect
    if (topic !== "*") {
      this.pendingSubscriptions.add(topic);
      this.sendAction("subscribe", topic);
    }

    return () => {
      this.listeners.get(topic)?.delete(handler);
      if (this.listeners.get(topic)?.size === 0) {
        this.listeners.delete(topic);
        if (topic !== "*") {
          this.pendingSubscriptions.delete(topic);
          this.sendAction("unsubscribe", topic);
        }
      }
    };
  }

  private sendAction(action: "subscribe" | "unsubscribe", topic: string) {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ action, topic }));
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

  private _intentionalClose = false;
}

export const wsManager = new WebSocketManager();
