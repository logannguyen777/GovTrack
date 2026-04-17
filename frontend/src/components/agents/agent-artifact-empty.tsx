"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";
import Link from "next/link";

export function AgentArtifactEmpty() {
  return (
    <div className="h-full flex flex-col items-center justify-center p-8 text-center">
      <Sparkles
        className="h-12 w-12 mb-4 opacity-30"
        style={{ color: "var(--text-muted)" }}
        aria-hidden="true"
      />
      <p
        className="font-medium mb-1 text-sm"
        style={{ color: "var(--text-primary)" }}
      >
        Chưa có agent đang chạy
      </p>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
        Khởi động pipeline AI từ trang{" "}
        <Link
          href="/intake"
          className="underline decoration-dotted hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] rounded-sm"
        >
          Tiếp nhận
        </Link>{" "}
        hoặc chọn 1 hồ sơ trong{" "}
        <Link
          href="/inbox"
          className="underline decoration-dotted hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] rounded-sm"
        >
          Hồ sơ đến
        </Link>
      </p>
    </div>
  );
}
