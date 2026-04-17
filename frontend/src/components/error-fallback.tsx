"use client";

import { useEffect } from "react";
import Link from "next/link";
import * as Sentry from "@sentry/nextjs";

interface ErrorFallbackProps {
  error: Error & { digest?: string };
  reset: () => void;
  /** Friendly label for where this boundary lives, e.g. "Portal público" */
  scope?: string;
}

export function ErrorFallback({ error, reset, scope }: ErrorFallbackProps) {
  const isDev = process.env.NODE_ENV !== "production";

  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div
      className="flex min-h-[400px] flex-col items-center justify-center gap-6 p-8 text-center"
      role="alert"
      aria-live="assertive"
    >
      {/* Icon */}
      <div
        className="flex h-16 w-16 items-center justify-center rounded-full"
        style={{ backgroundColor: "var(--accent-destructive)", opacity: 0.12 }}
        aria-hidden="true"
      >
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: "var(--accent-destructive)" }}
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>

      {/* Heading */}
      <div className="space-y-2">
        <h1
          className="text-xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          Đã xảy ra lỗi
        </h1>
        <p className="max-w-sm text-sm" style={{ color: "var(--text-secondary)" }}>
          {scope
            ? `Có lỗi xảy ra trong phần ${scope}. `
            : ""}
          Hệ thống đã ghi nhận lỗi này. Vui lòng thử lại hoặc quay về trang chủ.
        </p>
      </div>

      {/* Dev-only error details */}
      {isDev && (
        <details className="w-full max-w-lg rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] p-4 text-left">
          <summary className="cursor-pointer text-xs font-semibold text-[var(--text-muted)] select-none">
            Chi tiết lỗi (chỉ hiển thị trong môi trường development)
          </summary>
          <pre className="mt-3 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-[var(--accent-destructive)]">
            {error.message}
            {error.stack ? `\n\n${error.stack}` : ""}
          </pre>
          {error.digest && (
            <p className="mt-2 font-mono text-[10px] text-[var(--text-muted)]">
              Digest: {error.digest}
            </p>
          )}
        </details>
      )}

      {/* Prod: show digest only */}
      {!isDev && error.digest && (
        <p className="font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>
          Mã lỗi: {error.digest}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={reset}
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
          Về trang chủ
        </Link>
      </div>
    </div>
  );
}
