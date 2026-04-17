"use client";

import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { Lightbulb, X } from "lucide-react";
import { useOnboardingStore } from "@/lib/stores/onboarding-store";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface HelpHintBannerProps {
  id: string;
  icon?: LucideIcon;
  variant?: "info" | "tip" | "warn";
  children: React.ReactNode;
  dismissible?: boolean;
  className?: string;
}

// ---------------------------------------------------------------------------
// Variant styles
// ---------------------------------------------------------------------------

const VARIANT_STYLES: Record<NonNullable<HelpHintBannerProps["variant"]>, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-900",
  tip: "border-purple-200 bg-purple-50 text-purple-900",
  warn: "border-amber-200 bg-amber-50 text-amber-900",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HelpHintBanner({
  id,
  icon: Icon = Lightbulb,
  variant = "tip",
  children,
  dismissible = true,
  className,
}: HelpHintBannerProps) {
  // The onboarding store uses persist middleware (localStorage).
  // On SSR, localStorage doesn't exist → dismissedHints is always [].
  // On client after hydration, persist may restore a non-empty array.
  // This would cause React #418 (HTML mismatch) if we read dismissed state
  // during render without waiting for the client to mount.
  //
  // Fix: always render the banner during SSR and the first client render
  // (mounted = false), then after mount the real persisted state takes over.
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const dismissed = useOnboardingStore((s) =>
    mounted ? s.dismissedHints.includes(id) : false,
  );
  const dismiss = useOnboardingStore((s) => s.dismissHint);

  if (dismissed) return null;

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border p-4",
        VARIANT_STYLES[variant],
        className,
      )}
      role="note"
      aria-label="Gợi ý"
    >
      <Icon className="h-5 w-5 shrink-0 mt-0.5" aria-hidden="true" />
      <div className="flex-1 text-sm leading-relaxed">{children}</div>
      {dismissible && (
        <button
          type="button"
          onClick={() => dismiss(id)}
          className="opacity-60 hover:opacity-100 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current focus-visible:ring-offset-1 rounded"
          aria-label="Đóng gợi ý"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
