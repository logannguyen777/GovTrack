"use client";

import * as React from "react";
import { Play, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAgentArtifactStore } from "@/lib/stores/agent-artifact-store";
import { apiClient } from "@/lib/api";

interface TraceReplayButtonProps {
  caseId: string;
}

export function TraceReplayButton({ caseId }: TraceReplayButtonProps) {
  const [mode, setMode] = React.useState<"live" | "replaying">("live");
  const [speed, setSpeed] = React.useState<1 | 2 | 4>(1);
  const [progress, setProgress] = React.useState(0);
  const abortRef = React.useRef(false);

  const reset = useAgentArtifactStore((s) => s.reset);
  const ingest = useAgentArtifactStore((s) => s.ingestEvent);

  // Keep speed in a ref so the replay loop can read current value
  const speedRef = React.useRef(speed);
  React.useEffect(() => {
    speedRef.current = speed;
  }, [speed]);

  const startReplay = React.useCallback(async () => {
    // Uses apiClient so the Authorization Bearer header from localStorage
    // is attached — raw fetch() lands as 401 on protected endpoints.
    let body: { events?: Array<{ type: string; data: unknown; timestamp: string }> };
    try {
      body = await apiClient.get<{
        events?: Array<{ type: string; data: unknown; timestamp: string }>;
      }>(`/api/agents/trace/${caseId}/artifact`);
    } catch {
      return;
    }
    const events = body.events ?? [];
    if (!events.length) return;

    setMode("replaying");
    abortRef.current = false;
    reset(caseId);

    const t0 = new Date(events[0].timestamp).getTime();
    const wallStart = Date.now();

    for (let i = 0; i < events.length; i++) {
      if (abortRef.current) break;

      const e = events[i];
      const eventDelay = (new Date(e.timestamp).getTime() - t0) / speedRef.current;
      const elapsed = Date.now() - wallStart;
      const wait = Math.max(0, eventDelay - elapsed);

      if (wait > 0) {
        await new Promise<void>((r) => setTimeout(r, wait));
      }

      if (abortRef.current) break;

      ingest(caseId, { type: e.type, data: e.data });
      setProgress((i + 1) / events.length);
    }

    setMode("live");
    setProgress(0);
  }, [caseId, reset, ingest]);

  const stopReplay = React.useCallback(() => {
    abortRef.current = true;
    setMode("live");
    setProgress(0);
  }, []);

  if (mode === "live") {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => void startReplay()}
        aria-label="Phát lại trace"
      >
        <Play className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
        Phát lại
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2" role="status" aria-live="polite">
      {/* Progress bar */}
      <div
        className="relative h-1.5 w-24 rounded-full overflow-hidden"
        style={{ backgroundColor: "var(--border-subtle)" }}
        aria-label={`Đang phát lại: ${Math.round(progress * 100)}%`}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-150"
          style={{
            width: `${Math.round(progress * 100)}%`,
            background: "var(--gradient-qwen)",
          }}
        />
      </div>

      <span
        className="text-xs tabular-nums"
        style={{ color: "var(--text-muted)" }}
      >
        {Math.round(progress * 100)}%
      </span>

      {/* Speed selector */}
      <Select
        value={String(speed)}
        onValueChange={(v) => setSpeed(Number(v) as 1 | 2 | 4)}
      >
        <SelectTrigger
          className="h-7 w-16 text-xs"
          aria-label="Tốc độ phát lại"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="1">1×</SelectItem>
          <SelectItem value="2">2×</SelectItem>
          <SelectItem value="4">4×</SelectItem>
        </SelectContent>
      </Select>

      {/* Exit */}
      <Button
        variant="outline"
        size="sm"
        onClick={stopReplay}
        aria-label="Thoát phát lại"
      >
        <X className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
        Thoát
      </Button>
    </div>
  );
}
