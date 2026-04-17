"use client";

import * as React from "react";
import { FileText } from "lucide-react";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import type { CaseResponse } from "@/lib/types";

interface ComplianceHeaderProps {
  caseData: CaseResponse;
  complianceScore: number;
}

export function ComplianceHeader({
  caseData,
  complianceScore,
}: ComplianceHeaderProps) {
  return (
    <div className="space-y-3">
      {/* Title */}
      <div>
        <h1 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
          Không gian tuân thủ
        </h1>
        <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
          Xem xét mức độ tuân thủ pháp luật và đầy đủ của hồ sơ
        </p>
      </div>

      {/* Case info card */}
      <div className="rounded-lg border p-4" style={{ borderColor: "var(--border-subtle)", backgroundColor: "var(--bg-surface)" }}>
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 shrink-0" style={{ color: "var(--text-muted)" }} aria-hidden="true" />
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
              {caseData.code} · {caseData.tthc_code}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {caseData.applicant_name} · {caseData.status}
            </p>
          </div>
        </div>
      </div>

      {/* Compliance score */}
      <div className="rounded-lg border p-4" style={{ borderColor: "var(--border-subtle)", backgroundColor: "var(--bg-surface)" }}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Điểm tuân thủ</h3>
          <span className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
            <AnimatedCounter value={complianceScore} suffix="%" />
          </span>
        </div>
        <div
          className="mt-2 h-2 overflow-hidden rounded-full"
          style={{ backgroundColor: "var(--bg-subtle)" }}
          role="progressbar"
          aria-valuenow={complianceScore}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Điểm tuân thủ: ${complianceScore}%`}
        >
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${complianceScore}%`,
              backgroundColor:
                complianceScore >= 80
                  ? "var(--accent-success)"
                  : complianceScore >= 50
                    ? "var(--accent-warning)"
                    : "var(--accent-destructive)",
            }}
          />
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          {complianceScore >= 80
            ? "Hồ sơ đạt yêu cầu, có thể phê duyệt"
            : complianceScore >= 50
              ? "Hồ sơ cần bổ sung một số thành phần"
              : "Hồ sơ thiếu nhiều thành phần bắt buộc"}
        </p>
      </div>
    </div>
  );
}
