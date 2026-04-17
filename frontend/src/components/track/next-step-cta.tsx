"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, FileText, Eye } from "lucide-react";
import type { PublicCaseStatus } from "@/lib/types";

interface NextStepCTAProps {
  caseData: PublicCaseStatus;
}

export function NextStepCTA({ caseData }: NextStepCTAProps) {
  const router = useRouter();
  const { status } = caseData;

  if (status === "pending_supplement") {
    return (
      <div
        className="flex items-start gap-4 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4"
        role="alert"
      >
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
        <div className="flex-1">
          <p className="font-semibold text-amber-800">Cần bổ sung hồ sơ</p>
          <p className="mt-0.5 text-sm text-amber-700">
            Hồ sơ của bạn cần bổ sung thêm tài liệu. Vui lòng liên hệ cơ quan
            xử lý hoặc nộp bổ sung qua cổng trực tuyến.
          </p>
          <button
            type="button"
            onClick={() => router.push(`/submit/${caseData.code}`)}
            className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            <FileText size={14} />
            Bổ sung hồ sơ
          </button>
        </div>
      </div>
    );
  }

  if (status === "approved" || status === "published") {
    return (
      <div
        className="flex items-start gap-4 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4"
        role="status"
      >
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
        <div className="flex-1">
          <p className="font-semibold text-emerald-800">
            {status === "published" ? "Kết quả đã được ban hành" : "Hồ sơ được phê duyệt"}
          </p>
          <p className="mt-0.5 text-sm text-emerald-700">
            {status === "published"
              ? "Vui lòng đến nhận kết quả tại bộ phận Một cửa hoặc xem trực tuyến."
              : "Hồ sơ của bạn đã được phê duyệt. Kết quả sẽ sớm được ban hành."}
          </p>
          {status === "published" && (
            <button
              type="button"
              onClick={() =>
                window.open(`/api/public/cases/${caseData.code}/result`, "_blank")
              }
              className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              <Eye size={14} />
              Xem quyết định
            </button>
          )}
        </div>
      </div>
    );
  }

  if (status === "rejected") {
    return (
      <div
        className="flex items-start gap-4 rounded-xl border border-red-200 bg-red-50 px-5 py-4"
        role="alert"
      >
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
        <div className="flex-1">
          <p className="font-semibold text-red-800">Hồ sơ bị từ chối</p>
          <p className="mt-0.5 text-sm text-red-700">
            Vui lòng liên hệ cơ quan xử lý để biết lý do từ chối và hướng khắc
            phục.
          </p>
        </div>
      </div>
    );
  }

  return null;
}
