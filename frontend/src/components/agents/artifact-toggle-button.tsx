"use client";

import * as React from "react";
import { PanelRightOpen, PanelRightClose } from "lucide-react";
import { cn } from "@/lib/utils";
import { useArtifactPanelStore } from "@/lib/stores/artifact-panel-store";

// ---------------------------------------------------------------------------
// ArtifactToggleButton
//
// Shows PanelRightOpen / PanelRightClose based on isOpen state.
// Pulses an amber dot when hasActivePipeline is true.
// ---------------------------------------------------------------------------

export function ArtifactToggleButton() {
  const { isOpen, hasActivePipeline, toggle } = useArtifactPanelStore();

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={isOpen ? "Đóng panel AI" : "Mở panel AI"}
        aria-pressed={isOpen}
        onClick={toggle}
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)]",
          "transition-colors duration-[var(--duration-micro)]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
          isOpen
            ? "bg-[var(--bg-surface-raised)] text-[var(--text-primary)]"
            : "text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]",
        )}
      >
        {isOpen ? (
          <PanelRightClose size={18} aria-hidden="true" />
        ) : (
          <PanelRightOpen size={18} aria-hidden="true" />
        )}
      </button>

      {/* Active pipeline pulse dot */}
      {hasActivePipeline && (
        <span
          aria-hidden="true"
          className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full animate-pulse"
          style={{ backgroundColor: "var(--accent-warning)" }}
        />
      )}
    </div>
  );
}
