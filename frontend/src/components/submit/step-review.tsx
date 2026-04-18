"use client";

import * as React from "react";
import type { CitizenInfoData } from "./step-citizen-info";
import type { UploadFile } from "./step-upload";
import { AIReviewPanel } from "./ai-review-panel";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";

interface StepReviewProps {
  tthcCode: string;
  data: CitizenInfoData;
  files: UploadFile[];
  confirmed: boolean;
  onConfirmChange: (v: boolean) => void;
}

export function StepReview({
  tthcCode,
  data,
  files,
  confirmed,
  onConfirmChange,
}: StepReviewProps) {
  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold text-[var(--text-primary)]">
        Xem lại & nộp hồ sơ
      </h2>

      {/* Precheck hint */}
      <HelpHintBanner id="submit-precheck" variant="tip">
        Bấm <strong>AI kiểm tra hồ sơ</strong> bên dưới để phát hiện sớm thiếu sót trước khi nộp chính thức.
      </HelpHintBanner>

      {/* Summary table */}
      <div className="space-y-3 text-sm">
        <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
          <span className="text-[var(--text-muted)]">Thủ tục</span>
          <span className="font-mono text-[var(--text-primary)]">{tthcCode}</span>
        </div>
        <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
          <span className="text-[var(--text-muted)]">Họ tên</span>
          <span className="text-[var(--text-primary)]">{data.applicant_name || "—"}</span>
        </div>
        <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
          <span className="text-[var(--text-muted)]">CCCD</span>
          <span className="font-mono text-[var(--text-primary)]">
            {data.applicant_id_number || "—"}
          </span>
        </div>
        {data.applicant_phone && (
          <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
            <span className="text-[var(--text-muted)]">SĐT</span>
            <span className="text-[var(--text-primary)]">{data.applicant_phone}</span>
          </div>
        )}
        {data.applicant_address && (
          <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
            <span className="text-[var(--text-muted)]">Địa chỉ</span>
            <span className="text-right max-w-xs text-[var(--text-primary)]">
              {data.applicant_address}
            </span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-[var(--text-muted)]">Tài liệu</span>
          <span className="text-[var(--text-primary)]">{files.length} file</span>
        </div>
      </div>

      {/* AI precheck — pass ACTUAL uploaded filenames + full form data */}
      <AIReviewPanel
        tthcCode={tthcCode}
        formData={{
          applicant_name: data.applicant_name || "",
          applicant_id_number: data.applicant_id_number || "",
          applicant_phone: data.applicant_phone || "",
          applicant_address: data.applicant_address || "",
        }}
        uploadedFileUrls={files
          .map((f) => f.file?.name || "")
          .filter((n) => n.length > 0)}
      />

      {/* Confirmation */}
      <label className="flex cursor-pointer items-start gap-3 rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-4">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => onConfirmChange(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent-primary)] cursor-pointer"
          aria-required="true"
        />
        <span className="text-sm text-[var(--text-secondary)] leading-relaxed">
          Tôi xác nhận thông tin trên là chính xác và chịu trách nhiệm về tính
          trung thực của hồ sơ
        </span>
      </label>
    </div>
  );
}
