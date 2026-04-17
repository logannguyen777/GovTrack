"use client";

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIFillProgressProps {
  filled: number;
  total: number;
  className?: string;
}

export function AIFillProgress({ filled, total, className }: AIFillProgressProps) {
  if (total === 0 || filled === 0) return null;

  const pct = Math.round((filled / total) * 100);

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border px-4 py-2.5",
        className,
      )}
      style={{
        background: "var(--gradient-qwen-soft)",
        borderColor: "oklch(0.65 0.15 280 / 0.25)",
      }}
      role="status"
      aria-label={`AI đã điền ${filled} trên ${total} trường`}
    >
      <Sparkles size={14} className="shrink-0 text-purple-600" />
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-[var(--text-primary)]">
            AI đã điền{" "}
            <span className="text-purple-700">
              {filled}/{total}
            </span>{" "}
            trường
          </span>
          <span className="text-xs text-[var(--text-muted)]">{pct}%</span>
        </div>
        <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--bg-subtle)]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, background: "var(--gradient-qwen)" }}
          />
        </div>
      </div>
    </div>
  );
}
