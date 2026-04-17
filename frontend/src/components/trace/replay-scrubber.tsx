"use client";

/**
 * ReplayScrubber — scrub trace timeline from T0→now.
 *
 * Controlled slider that emits a `timestamp` value (ISO string). Parent
 * filters trace steps / subgraph visibility to this cutoff.
 *
 * Shown on /trace/[case_id] so judges can rewind pipeline execution and
 * see each step light up in order.
 */

import * as React from "react";
import { Play, Pause, SkipBack, SkipForward } from "lucide-react";

export interface ReplayStep {
  started_at: string;
  agent_name: string;
  status: string;
}

interface ReplayScrubberProps {
  steps: ReplayStep[];
  onCutoffChange: (iso: string | null) => void;
  className?: string;
}

export function ReplayScrubber({ steps, onCutoffChange, className }: ReplayScrubberProps) {
  const sorted = React.useMemo(
    () => [...steps].filter((s) => s.started_at).sort(
      (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
    ),
    [steps],
  );

  const [idx, setIdx] = React.useState(sorted.length); // Start at "now"
  const [playing, setPlaying] = React.useState(false);

  React.useEffect(() => {
    // Clamp idx when steps change
    if (idx > sorted.length) setIdx(sorted.length);
  }, [sorted.length, idx]);

  React.useEffect(() => {
    if (idx >= sorted.length) {
      onCutoffChange(null);
    } else {
      const step = sorted[idx];
      onCutoffChange(step?.started_at ?? null);
    }
  }, [idx, sorted, onCutoffChange]);

  React.useEffect(() => {
    if (!playing) return;
    const tick = setInterval(() => {
      setIdx((i) => {
        if (i >= sorted.length) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, 900);
    return () => clearInterval(tick);
  }, [playing, sorted.length]);

  if (sorted.length === 0) return null;

  const currentStep = sorted[Math.min(idx, sorted.length - 1)];
  const label =
    idx >= sorted.length
      ? `Live · ${sorted.length} bước`
      : `Bước ${idx + 1}/${sorted.length} · ${currentStep?.agent_name ?? "?"}`;

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 ${className ?? ""}`}
    >
      <button
        type="button"
        aria-label="Về đầu"
        onClick={() => {
          setIdx(0);
          setPlaying(false);
        }}
        className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)]"
      >
        <SkipBack size={14} />
      </button>
      <button
        type="button"
        aria-label={playing ? "Tạm dừng replay" : "Phát replay"}
        onClick={() => {
          if (idx >= sorted.length) setIdx(0);
          setPlaying((v) => !v);
        }}
        className="flex h-7 w-7 items-center justify-center rounded-md bg-[var(--accent-primary)] text-white hover:opacity-90"
      >
        {playing ? <Pause size={14} /> : <Play size={14} />}
      </button>
      <button
        type="button"
        aria-label="Tới cuối"
        onClick={() => {
          setIdx(sorted.length);
          setPlaying(false);
        }}
        className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)]"
      >
        <SkipForward size={14} />
      </button>

      <input
        type="range"
        min={0}
        max={sorted.length}
        step={1}
        value={idx}
        onChange={(e) => {
          setIdx(Number(e.target.value));
          setPlaying(false);
        }}
        aria-label="Replay timeline"
        className="flex-1 accent-[var(--accent-primary)]"
      />

      <span className="shrink-0 font-mono text-[10px] text-[var(--text-muted)]">
        {label}
      </span>
    </div>
  );
}
