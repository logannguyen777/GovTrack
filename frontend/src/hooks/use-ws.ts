"use client";

import { useEffect, useState, useCallback } from "react";
import { wsManager } from "@/lib/ws";
import { useAuth } from "@/components/providers/auth-provider";
import type { WSMessage } from "@/lib/types";

// ---- Hooks ----

/**
 * Manages the lifecycle of the WebSocket connection.
 *
 * Mount this once inside an authenticated layout. It connects when a valid
 * token is available and disconnects when the component unmounts (e.g. logout
 * or route away from the authenticated shell).
 *
 * Usage: place `<WSConnectionGate />` inside `(internal)/layout.tsx`, or call
 * `useWSConnection()` directly from the root internal layout component.
 */
export function useWSConnection(): void {
  const { token, user } = useAuth();

  useEffect(() => {
    // Only open the socket when we have a verified authenticated session
    if (!token || !user) return;

    wsManager.connect(token);

    return () => {
      wsManager.disconnect();
    };
    // Re-connect if the token rotates (e.g. token refresh)
  }, [token, user]);
}

/**
 * Subscribe to a WebSocket topic and invoke `handler` on every message.
 *
 * The subscription is registered when the component mounts and automatically
 * cleaned up on unmount. The handler reference is intentionally excluded from
 * the dep-array — wrap it in `useCallback` at the call site if you need
 * referential stability.
 *
 * @param topic   - Topic name, e.g. `"trace"`, `"notifications"`, `"audit"`, or `"*"`
 * @param handler - Called with each `WSMessage` received on the topic
 *
 * @example
 * useWSTopic(`trace:${caseId}`, (msg) => {
 *   dispatch({ type: msg.event, payload: msg.data });
 * });
 */
export function useWSTopic(
  topic: string,
  handler: (msg: WSMessage) => void,
): void {
  useEffect(() => {
    if (!topic) return;

    const unsubscribe = wsManager.subscribe(topic, handler);
    return unsubscribe;
    // handler is intentionally omitted — callers should useCallback if needed
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic]);
}

/**
 * Returns the current WebSocket connection state.
 * Polls every 2 seconds for state changes.
 */
export function useWSState(): "connected" | "connecting" | "disconnected" {
  const [state, setState] = useState<"connected" | "connecting" | "disconnected">(
    "disconnected",
  );

  const check = useCallback(() => {
    setState(wsManager.getState());
  }, []);

  useEffect(() => {
    check();
    const interval = setInterval(check, 2000);
    return () => clearInterval(interval);
  }, [check]);

  return state;
}
