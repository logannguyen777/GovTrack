"use client";

import { ErrorFallback } from "@/components/error-fallback";

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
      <ErrorFallback error={error} reset={reset} scope="xác thực" />
    </div>
  );
}
