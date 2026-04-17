"use client";

/**
 * Shared error fallback component used by all Next.js error boundaries.
 * Re-exports the root-level ErrorFallback for backwards compatibility,
 * and provides a typed wrapper with the exact props shape required by the spec.
 */

import { useEffect } from "react";
import Link from "next/link";
import * as Sentry from "@sentry/nextjs";
import { AlertTriangle } from "lucide-react";

export interface ErrorFallbackProps {
  error: Error & { digest?: string };
  onReset: () => void;
  title?: string;
}

export function ErrorFallback({ error, onReset, title }: ErrorFallbackProps) {
  const isDev = process.env.NODE_ENV === "development";

  useEffect(() => {
    try {
      Sentry.captureException(error);
    } catch {
      // Sentry not yet initialised — swallow silently.
    }
  }, [error]);

  return (
    <div
      className="flex min-h-[400px] flex-col items-center justify-center gap-6 p-8 text-center"
      role="alert"
      aria-live="assertive"
    >
      {/* Alert icon */}
      <div
        className="flex h-16 w-16 items-center justify-center rounded-full"
        style={{ backgroundColor: "var(--accent-destructive, #dc2626)", opacity: 0.12 }}
        aria-hidden="true"
      >
        <AlertTriangle
          size={32}
          style={{ color: "var(--accent-destructive, #dc2626)", opacity: 1 / 0.12 }}
          aria-hidden="true"
        />
      </div>

      {/* Heading + description */}
      <div className="space-y-2">
        <h2
          className="text-xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          {title ?? "Đã xảy ra lỗi"}
        </h2>
        <p className="max-w-sm text-sm" style={{ color: "var(--text-secondary)" }}>
          Hệ thống đã ghi nhận lỗi này. Vui lòng thử lại hoặc quay về trang chủ.
        </p>
      </div>

      {/* Dev-only error message */}
      {isDev && error.message && (
        <p
          className="max-w-lg rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-3 py-2 font-mono text-[11px]"
          style={{ color: "var(--accent-destructive, #dc2626)" }}
        >
          {error.message}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={onReset}
          className="rounded-md px-4 py-2 text-sm font-medium text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2"
          style={{ backgroundColor: "var(--accent-primary)" }}
          aria-label="Thử lại"
        >
          Thử lại
        </button>
        <Link
          href="/"
          className="rounded-md border px-4 py-2 text-sm font-medium transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2"
          style={{
            borderColor: "var(--border-default)",
            color: "var(--text-secondary)",
          }}
        >
          Quay về trang chủ
        </Link>
      </div>
    </div>
  );
}
