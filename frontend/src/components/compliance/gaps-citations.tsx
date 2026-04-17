"use client";

import * as React from "react";
import { GapCard } from "@/components/cases/gap-card";
import { CitationBadge } from "@/components/cases/citation-badge";
import type { Gap } from "@/components/cases/gap-card";
import type { Citation } from "@/components/cases/citation-badge";

interface GapsCitationsProps {
  gaps: Gap[];
  citations: Citation[];
  traceStatus?: string;
}

export function GapsCitations({ gaps, citations, traceStatus }: GapsCitationsProps) {
  return (
    <div className="space-y-4">
      {/* Gaps */}
      <section>
        <h2 className="font-semibold" style={{ color: "var(--text-primary)" }}>
          Thiếu sót ({gaps.length})
        </h2>
        <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
          Các thiếu sót phát hiện bởi hệ thống AI. Mỗi thiếu sót cần được khắc phục trước khi phê duyệt
        </p>

        {gaps.length === 0 ? (
          <div
            className="mt-2 rounded-md border p-4 text-center text-sm"
            style={{
              borderColor: "var(--border-subtle)",
              backgroundColor: "var(--bg-surface)",
              color: "var(--text-muted)",
            }}
          >
            {traceStatus === "completed"
              ? "Không phát hiện thiếu sót"
              : "Đang kiểm tra..."}
          </div>
        ) : (
          <div className="mt-2 space-y-2">
            {gaps.map((gap) => (
              <GapCard key={gap.id} gap={gap} />
            ))}
          </div>
        )}
      </section>

      {/* Citations */}
      <section>
        <h2 className="font-semibold" style={{ color: "var(--text-primary)" }}>
          Căn cứ pháp lý ({citations.length})
        </h2>
        <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
          Căn cứ pháp lý liên quan đến hồ sơ này
        </p>

        {citations.length === 0 ? (
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
            {traceStatus === "completed"
              ? "Không có trích dẫn pháp lý"
              : "Đang tra cứu..."}
          </p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            {citations.map((c, i) => (
              <CitationBadge key={i} citation={c} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
