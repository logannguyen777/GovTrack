"use client";

import * as React from "react";
import { wsManager } from "@/lib/ws";

export type ActivityType = "llm" | "vector" | "graph" | "ocr" | "oss" | "cache";

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type: ActivityType;
  label: string;
  detail?: string;
  duration_ms?: number;
  model?: string;
}

const TOPIC = "public:system:activity";
const MAX_EVENTS = 30;

/**
 * Subscribes to the public:system:activity WS topic and returns a bounded
 * rolling feed of ActivityEvent. Safe on public (unauth) pages — backend
 * allows `public:*` topics without auth.
 */
export function useActivityFeed(): ActivityEvent[] {
  const [events, setEvents] = React.useState<ActivityEvent[]>([]);

  React.useEffect(() => {
    // Open anonymous connection if no existing one
    wsManager.connect("");

    const unsubscribe = wsManager.subscribe(TOPIC, (msg) => {
      const data = (msg.data ?? {}) as Partial<ActivityEvent>;
      if (!data.type || !data.label) return;
      const evt: ActivityEvent = {
        id:
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID().slice(0, 8)
            : Math.random().toString(36).slice(2, 10),
        timestamp: data.timestamp ?? new Date().toISOString(),
        type: data.type as ActivityType,
        label: data.label,
        detail: data.detail,
        duration_ms: data.duration_ms,
        model: data.model,
      };
      setEvents((prev) => [evt, ...prev].slice(0, MAX_EVENTS));
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return events;
}
