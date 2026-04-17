"use client";

import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// QuickIntentChip
// ---------------------------------------------------------------------------

interface QuickIntentChipProps {
  label: string;
  icon?: LucideIcon;
  onClick: () => void;
  variant?: "default" | "qwen";
}

export function QuickIntentChip({
  label,
  icon: Icon,
  onClick,
  variant = "default",
}: QuickIntentChipProps) {
  const isQwen = variant === "qwen";

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5",
        "text-sm font-medium whitespace-nowrap select-none",
        "transition-all duration-150",
        "hover:-translate-y-0.5 hover:shadow-sm",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
        "active:translate-y-0",
        isQwen
          ? "text-white border-transparent"
          : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-default)]",
      )}
      style={
        isQwen
          ? {
              background: "var(--gradient-qwen)",
              boxShadow: "0 2px 8px rgba(124,58,237,0.2)",
            }
          : undefined
      }
    >
      {Icon && <Icon size={14} aria-hidden="true" />}
      {label}
    </button>
  );
}
