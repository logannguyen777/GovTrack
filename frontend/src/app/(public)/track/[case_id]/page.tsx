"use client";

import { use } from "react";
import { usePublicCase } from "@/hooks/use-public";
import { Phone } from "lucide-react";

const STAGES = [
  { key: "submitted", label: "Tiếp nhận" },
  { key: "classifying", label: "Phân loại" },
  { key: "extracting", label: "Kiểm tra" },
  { key: "processing", label: "Xử lý" },
  { key: "completed", label: "Kết quả" },
];

const STATUS_TO_STAGE: Record<string, number> = {
  submitted: 0,
  classifying: 1,
  extracting: 2,
  gap_checking: 2,
  pending_supplement: 2,
  legal_review: 3,
  drafting: 3,
  leader_review: 3,
  consultation: 3,
  approved: 4,
  rejected: 4,
  published: 4,
};

const STATUS_DESCRIPTIONS: Record<string, string> = {
  submitted: "Hồ sơ đã được tiếp nhận vào hệ thống",
  classifying: "Hệ thống đang phân loại và kiểm tra thành phần hồ sơ",
  extracting: "Đang trích xuất thông tin từ tài liệu",
  gap_checking: "Đang kiểm tra tính đầy đủ và hợp lệ theo quy định",
  pending_supplement: "Hồ sơ cần bổ sung thêm tài liệu",
  legal_review: "Đang xem xét cơ sở pháp lý",
  drafting: "Đang soạn thảo văn bản quyết định",
  leader_review: "Đang chờ lãnh đạo phê duyệt",
  consultation: "Đang xin ý kiến các cơ quan liên quan",
  approved: "Hồ sơ đã được phê duyệt",
  rejected: "Hồ sơ bị từ chối — vui lòng liên hệ để biết lý do",
  published:
    "Kết quả đã được ban hành — vui lòng đến nhận tại bộ phận Một cửa",
};

export default function CaseTrackingPage({
  params,
}: {
  params: Promise<{ case_id: string }>;
}) {
  const { case_id } = use(params);
  const { data: caseData, isLoading, error } = usePublicCase(case_id);

  const currentStage = caseData
    ? STATUS_TO_STAGE[caseData.status] ?? 0
    : -1;

  const statusDescription = caseData
    ? STATUS_DESCRIPTIONS[caseData.status] ?? ""
    : "";

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">
        Tra cứu hồ sơ
      </h1>
      <p className="mt-1 text-sm text-[var(--text-muted)]">
        Mã hồ sơ: <span className="font-mono">{case_id}</span>
      </p>

      {isLoading && (
        <div className="mt-8 space-y-3" aria-live="polite" aria-busy="true">
          <div className="h-24 animate-pulse rounded-lg bg-[var(--bg-surface)]" />
          <div className="h-48 animate-pulse rounded-lg bg-[var(--bg-surface)]" />
          <p className="text-center text-sm text-[var(--text-muted)]">
            Đang tải thông tin hồ sơ...
          </p>
        </div>
      )}

      {error && (
        <div
          className="mt-8 rounded-md border border-[var(--accent-destructive)]/30 bg-[var(--accent-destructive)]/5 p-5"
          role="alert"
        >
          <p className="font-medium text-[var(--accent-destructive)]">
            Không tìm thấy hồ sơ
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Không tìm thấy hồ sơ với mã{" "}
            <span className="font-mono font-semibold">{case_id}</span>. Vui
            lòng kiểm tra lại mã hồ sơ. Nếu cần hỗ trợ, liên hệ Tổng đài:{" "}
            <a
              href="tel:1900xxxx"
              className="font-semibold text-[var(--accent-primary)] hover:underline"
            >
              1900.xxxx
            </a>
          </p>
        </div>
      )}

      {caseData && (
        <div className="mt-8 space-y-6">
          {/* Status card */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-[var(--text-secondary)]">
                  Trạng thái hiện tại
                </p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                  {caseData.current_step ?? caseData.status}
                </p>
                {statusDescription && (
                  <p className="mt-1.5 text-sm text-[var(--text-secondary)]">
                    {statusDescription}
                  </p>
                )}
              </div>
              {caseData.estimated_completion && (
                <div className="shrink-0 text-right">
                  <p className="text-sm text-[var(--text-secondary)]">
                    Dự kiến hoàn thành
                  </p>
                  <p className="mt-1 text-sm font-medium text-[var(--text-primary)]">
                    {new Date(caseData.estimated_completion).toLocaleDateString(
                      "vi-VN",
                    )}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
            <h2 className="mb-4 font-semibold text-[var(--text-primary)]">
              Tiến trình xử lý
            </h2>
            <div className="space-y-0" role="list">
              {STAGES.map((stage, i) => {
                const status =
                  i < currentStage
                    ? "completed"
                    : i === currentStage
                      ? "active"
                      : "pending";
                const dotClass =
                  status === "completed"
                    ? "bg-[var(--accent-success)]"
                    : status === "active"
                      ? "bg-[var(--accent-primary)] animate-pulse"
                      : "bg-[var(--border-default)]";

                return (
                  <div key={stage.key} className="flex gap-3" role="listitem">
                    <div className="flex flex-col items-center">
                      <div
                        className={`h-3 w-3 rounded-full ${dotClass}`}
                        aria-label={
                          status === "completed"
                            ? "Đã hoàn thành"
                            : status === "active"
                              ? "Đang xử lý"
                              : "Chưa đến"
                        }
                      />
                      {i < STAGES.length - 1 && (
                        <div className="w-px flex-1 bg-[var(--border-subtle)]" />
                      )}
                    </div>
                    <div className="pb-6">
                      <p
                        className={`text-sm font-medium ${status === "pending" ? "text-[var(--text-muted)]" : "text-[var(--text-primary)]"}`}
                      >
                        {stage.label}
                        {status === "active" && (
                          <span className="ml-2 rounded-full bg-[var(--accent-primary)]/10 px-2 py-0.5 text-xs font-normal text-[var(--accent-primary)]">
                            Đang xử lý
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Support footer — always visible */}
      <div className="mt-10 flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-5 py-4">
        <Phone className="h-5 w-5 shrink-0 text-[var(--accent-primary)]" />
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">
            Cần hỗ trợ?
          </p>
          <p className="text-sm text-[var(--text-secondary)]">
            Liên hệ Tổng đài:{" "}
            <a
              href="tel:1900xxxx"
              className="font-semibold text-[var(--accent-primary)] hover:underline"
            >
              1900.xxxx
            </a>{" "}
            <span className="text-[var(--text-muted)]">
              (Thứ Hai – Thứ Sáu, 7:30 – 17:00)
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
