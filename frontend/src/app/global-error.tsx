"use client";

// global-error.tsx replaces the root layout when the root layout itself throws.
// It MUST include <html> and <body>.
import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const isDev = process.env.NODE_ENV !== "production";

  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="vi">
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, sans-serif",
          background: "#0f172a",
          color: "#f8fafc",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          textAlign: "center",
          padding: "2rem",
        }}
      >
        <div style={{ maxWidth: 480 }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.75rem" }}>
            Đã xảy ra lỗi nghiêm trọng
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
            Ứng dụng gặp lỗi không thể khôi phục. Vui lòng tải lại trang.
          </p>
          {isDev && error.message && (
            <pre
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "0.5rem",
                padding: "1rem",
                fontSize: "0.75rem",
                color: "#f87171",
                textAlign: "left",
                overflowX: "auto",
                marginBottom: "1.5rem",
                whiteSpace: "pre-wrap",
              }}
            >
              {error.message}
            </pre>
          )}
          {!isDev && error.digest && (
            <p style={{ color: "#64748b", fontSize: "0.75rem", marginBottom: "1.5rem" }}>
              Mã lỗi: {error.digest}
            </p>
          )}
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
            <button
              onClick={reset}
              style={{
                background: "#3b82f6",
                color: "#fff",
                border: "none",
                borderRadius: "0.375rem",
                padding: "0.5rem 1rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Thử lại
            </button>
            <a
              href="/"
              style={{
                border: "1px solid #334155",
                color: "#94a3b8",
                borderRadius: "0.375rem",
                padding: "0.5rem 1rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                textDecoration: "none",
              }}
            >
              Về trang chủ
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
