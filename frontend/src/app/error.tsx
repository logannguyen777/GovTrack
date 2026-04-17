"use client";

import { ErrorFallback } from "@/components/error-fallback";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen bg-[var(--bg-app)]">
      <ErrorFallback error={error} reset={reset} />
    </div>
  );
}
