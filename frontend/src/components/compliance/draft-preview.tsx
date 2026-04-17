"use client";

/**
 * DraftPreview — NĐ 30/2020 công văn preview + checklist.
 * Backend: GET /api/assistant/draft-preview/{case_id}
 *
 * Shown inside Compliance Detail to prove the system emits properly
 * formatted official documents (Quốc hiệu, số/ký hiệu, thể thức v.v.)
 * for the judges from MoHA / government track.
 *
 * Security: all HTML from the backend is sanitized client-side via DOMPurify
 * (isomorphic-dompurify, works in SSR + browser) before any innerHTML injection.
 */

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Download, CheckCircle2, XCircle, Loader2, ShieldCheck } from "lucide-react";
import DOMPurify from "isomorphic-dompurify";
import { apiClient } from "@/lib/api";

/** Allowed HTML tags for official Vietnamese government documents (NĐ 30/2020). */
const DOMPURIFY_ALLOWED_TAGS = [
  "p", "b", "i", "u",
  "h1", "h2", "h3", "h4",
  "ol", "ul", "li",
  "br", "strong", "em",
  "span", "div",
  "table", "tr", "td", "th", "thead", "tbody",
];

const DOMPURIFY_ALLOWED_ATTR = ["class", "style"];

/** Sanitize HTML using DOMPurify with the govflow allowed-list. */
function sanitizeHtml(raw: string): string {
  // RETURN_DOM: false → always returns a plain string (required for dangerouslySetInnerHTML).
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: DOMPURIFY_ALLOWED_TAGS,
    ALLOWED_ATTR: DOMPURIFY_ALLOWED_ATTR,
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false,
  }) as string;
}

interface NghiDinh30Check {
  rule: string;
  status: boolean;
  detail: string;
}

interface DraftPreviewResponse {
  doc_title: string;
  doc_number: string;
  issue_date: string;
  content_html: string;
  checklist: NghiDinh30Check[];
  score: number;
}

interface DraftPreviewProps {
  caseId: string;
}

export function DraftPreview({ caseId }: DraftPreviewProps) {
  const { data, isLoading, error } = useQuery<DraftPreviewResponse>({
    queryKey: ["draft-preview", caseId],
    queryFn: () =>
      apiClient.get<DraftPreviewResponse>(
        `/api/assistant/draft-preview/${encodeURIComponent(caseId)}`,
      ),
    enabled: Boolean(caseId),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <Loader2 className="h-4 w-4 animate-spin text-[var(--accent-primary)]" />
        <p className="text-xs text-[var(--text-muted)]">
          Đang render văn bản theo NĐ 30/2020...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
        Không tải được bản nháp.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
      {/* Document preview */}
      <div className="lg:col-span-3">
        <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] pb-2">
          <FileText size={14} className="text-[var(--accent-primary)]" />
          <p className="text-xs font-semibold text-[var(--text-primary)]">
            {data.doc_title}
          </p>
          <span className="ml-auto font-mono text-[10px] text-[var(--text-muted)]">
            {data.doc_number}
          </span>
        </div>

        <div
          className="mt-3 max-h-[600px] overflow-y-auto rounded-lg border border-[var(--border-subtle)] bg-white p-6 text-sm shadow-inner dark:bg-[var(--bg-surface)]"
          // content_html is sanitized before injection — removes scripts, event
          // handlers, data: URIs, and any tag/attribute not on the allowed-list.
          dangerouslySetInnerHTML={{ __html: sanitizeHtml(data.content_html) }}
        />

        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              // Sanitize both the title (for the <title> element) and body HTML
              // before writing into the blob to prevent stored-XSS in the print view.
              const safeTitle = data.doc_title.replace(/[<>"'&]/g, (c) =>
                ({ "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "&": "&amp;" }[c] ?? c),
              );
              const safeBody = sanitizeHtml(data.content_html);
              const blob = new Blob(
                [
                  `<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>${safeTitle}</title></head><body>${safeBody}</body></html>`,
                ],
                { type: "text/html" },
              );
              const url = URL.createObjectURL(blob);
              window.open(url, "_blank");
            }}
            className="flex items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
          >
            <Download size={12} /> Mở bản in
          </button>
          <span className="text-[10px] text-[var(--text-muted)]">
            Bản nháp dùng thể thức NĐ 30/2020 · Cán bộ thẩm quyền ký số trước khi ban hành
          </span>
        </div>
      </div>

      {/* NĐ 30/2020 checklist */}
      <div className="lg:col-span-2">
        <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] pb-2">
          <ShieldCheck size={14} className="text-emerald-600 dark:text-emerald-300" />
          <p className="text-xs font-semibold text-[var(--text-primary)]">
            NĐ 30/2020 · checklist thể thức
          </p>
          <span
            className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold ${
              data.score === 100
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200"
                : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-200"
            }`}
          >
            {data.score}% đạt
          </span>
        </div>

        <ul className="mt-2 divide-y divide-[var(--border-subtle)] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          {data.checklist.map((c) => (
            <li key={c.rule} className="flex items-start gap-2 px-3 py-2">
              {c.status ? (
                <CheckCircle2
                  size={14}
                  className="mt-0.5 shrink-0 text-emerald-500"
                  aria-hidden
                />
              ) : (
                <XCircle
                  size={14}
                  className="mt-0.5 shrink-0 text-red-500"
                  aria-hidden
                />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-[var(--text-primary)]">
                  {c.rule}
                </p>
                <p className="truncate text-[10px] text-[var(--text-muted)]">
                  {c.detail}
                </p>
              </div>
            </li>
          ))}
        </ul>

        <p className="mt-2 text-[10px] text-[var(--text-muted)]">
          Cơ sở pháp lý: Điều 8, Nghị định 30/2020/NĐ-CP về công tác văn thư.
        </p>
      </div>
    </div>
  );
}
