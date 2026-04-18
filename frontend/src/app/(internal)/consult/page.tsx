"use client";

import { useMemo, useState, useEffect } from "react";
import { Sparkles, Clock, AlertTriangle, CheckCircle2, XCircle, FileText, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider";
import { useConsultInbox, useSubmitConsultOpinion, type ConsultInboxItem } from "@/hooks/use-consult";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

interface Precedent {
  case_id: string;
  tthc_code: string;
  status: string;
  processing_days: number | null;
  submitted_at: string | null;
  completed_at: string | null;
  outcome_label: string;
}

function PrecedentCasesPanel({ caseId }: { caseId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["precedent-cases", caseId],
    queryFn: () =>
      apiClient.get<Precedent[]>(
        `/api/assistant/precedent-cases/${encodeURIComponent(caseId)}`,
      ),
    enabled: !!caseId,
    staleTime: 60_000,
  });

  const router = useRouter();
  const rows = (data ?? []).slice(0, 5);

  return (
    <section className="mt-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-app)] p-4">
      <h3 className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
        <FileText size={14} /> Case tương tự đã xử lý ({rows.length})
      </h3>
      {isLoading && (
        <p className="mt-2 text-xs text-[var(--text-muted)]">Đang tải...</p>
      )}
      {!isLoading && rows.length === 0 && (
        <p className="mt-2 text-xs text-[var(--text-muted)]">
          Chưa có case tương tự đã hoàn tất để tham khảo.
        </p>
      )}
      {rows.length > 0 && (
        <ul className="mt-2 divide-y divide-[var(--border-subtle)]">
          {rows.map((p) => (
            <li
              key={p.case_id}
              className="flex items-center justify-between gap-2 py-2 text-xs"
            >
              <button
                type="button"
                onClick={() => router.push(`/compliance/${p.case_id}`)}
                className="truncate font-mono text-[var(--accent-primary)] hover:underline"
              >
                {p.case_id}
              </button>
              <span className="flex items-center gap-2 text-[var(--text-muted)]">
                {p.processing_days != null && (
                  <span>{p.processing_days} ngày</span>
                )}
                <span
                  className={cn(
                    "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                    p.status === "approved" || p.status === "published"
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200"
                      : "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-200",
                  )}
                >
                  {p.outcome_label}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// Surface WS opinion_received events as an in-app toast so Tuan knows
// when phap che has replied without having to refresh.
function useOpinionReceivedToast() {
  useEffect(() => {
    import("@/lib/ws").then(({ wsManager }) => {
      const off = wsManager.subscribe("public:system:activity", (msg) => {
        const d = msg.data as Record<string, unknown> | undefined;
        if (
          d &&
          typeof d.event === "string" &&
          d.event.toLowerCase().includes("opinion_received")
        ) {
          toast.success("Đã nhận ý kiến mới từ phòng chuyên môn");
        }
      });
      return () => off();
    });
  }, []);
}

type Stance = "agree" | "disagree" | "abstain";

function slaBadge(deadline: string): { label: string; tone: "danger" | "warn" | "ok" } {
  if (!deadline) return { label: "Không có hạn", tone: "ok" };
  const hrs = (new Date(deadline).getTime() - Date.now()) / 36e5;
  if (isNaN(hrs)) return { label: "—", tone: "ok" };
  if (hrs < 0) return { label: `Quá hạn ${Math.abs(hrs).toFixed(0)}h`, tone: "danger" };
  if (hrs < 24) return { label: `Còn ${hrs.toFixed(0)}h`, tone: "danger" };
  if (hrs < 72) return { label: `Còn ${Math.floor(hrs / 24)} ngày`, tone: "warn" };
  return { label: `Còn ${Math.floor(hrs / 24)} ngày`, tone: "ok" };
}

function urgencyBadge(u: string) {
  const map: Record<string, { label: string; cls: string }> = {
    low: { label: "Thấp", cls: "bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300" },
    normal: { label: "Thường", cls: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-200" },
    high: { label: "Khẩn", cls: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200" },
    urgent: { label: "Hoả tốc", cls: "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-200" },
  };
  return map[u] ?? map.normal;
}

export default function ConsultPage() {
  const { user } = useAuth();
  const router = useRouter();
  useOpinionReceivedToast();
  const { data: items = [], isLoading, error } = useConsultInbox("pending");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [stance, setStance] = useState<Stance>("agree");
  const [opinion, setOpinion] = useState("");
  const [aiDrafting, setAiDrafting] = useState(false);
  const submit = useSubmitConsultOpinion();

  const selected: ConsultInboxItem | undefined = useMemo(
    () => items.find((it) => it.request_id === selectedId) ?? items[0],
    [items, selectedId],
  );

  async function handleAiDraft() {
    if (!selected) return;
    setAiDrafting(true);
    try {
      const draft = await apiClient.post<{ draft: string }>(
        "/api/assistant/draft-opinion",
        {
          case_id: selected.case_id ?? selected.case_code,
          case_code: selected.case_code,
          stance,
          question: selected.main_question ?? "",
          context: selected.context_summary ?? "",
        },
      );
      setOpinion(draft.draft);
      toast.success("AI đã soạn ý kiến — xin vui lòng rà soát trước khi gửi");
    } catch (e) {
      // Fallback template when AI endpoint unavailable
      const tmpl =
        stance === "agree"
          ? `Sau khi nghiên cứu hồ sơ ${selected.case_code} và các căn cứ pháp lý liên quan, ` +
            `Phòng Pháp chế nhất trí với đề xuất của đơn vị chủ trì. ` +
            `Hồ sơ đã đáp ứng các yêu cầu theo quy định hiện hành.`
          : stance === "disagree"
            ? `Qua rà soát hồ sơ ${selected.case_code}, Phòng Pháp chế nhận thấy chưa đủ cơ sở để chấp thuận. ` +
              `Đề nghị đơn vị chủ trì bổ sung tài liệu và làm rõ: "${selected.main_question}".`
            : `Nội dung xin ý kiến ${selected.case_code} vượt ngoài phạm vi tham mưu. ` +
              `Đề nghị chuyển đến cơ quan chuyên môn có thẩm quyền.`;
      setOpinion(tmpl);
      console.error("AI draft fallback", e);
      toast.success("Đã soạn mẫu ý kiến (AI offline) — vui lòng chỉnh sửa");
    } finally {
      setAiDrafting(false);
    }
  }

  async function handleSubmit() {
    if (!selected || !opinion.trim() || !user) return;
    try {
      await submit.mutateAsync({
        requestId: selected.request_id,
        body: {
          department_id: (user.departments?.[0] as string) || "DEPT-PHAPCHE",
          department_name: "Phòng Pháp chế",
          stance,
          opinion: opinion.trim(),
          citation: [],
          confidence: 0.9,
          author_name: user.username,
        },
      });
      toast.success("Đã gửi ý kiến — công văn phản hồi tự động");
      setOpinion("");
      setSelectedId(null);
    } catch (err) {
      toast.error(`Không gửi được: ${err instanceof Error ? err.message : "unknown"}`);
    }
  }

  return (
    <div className="flex h-[calc(100vh-112px)] gap-4 p-6">
      {/* Left pane — inbox list */}
      <aside className="flex w-[38%] min-w-[360px] flex-col overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <header className="border-b border-[var(--border-subtle)] px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Hộp xin ý kiến
              </h2>
              <p className="text-xs text-[var(--text-muted)]">
                {items.length} yêu cầu đang chờ · phòng {user?.departments?.[0] ?? "Pháp chế"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => router.push("/compliance/CASE-2026-0001")}
                className="flex items-center gap-1.5 rounded-md border border-purple-300 bg-gradient-to-r from-purple-600 to-violet-600 px-3 py-1 text-xs font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
                title="Mở case CPXD mẫu có gap PCCC"
              >
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                Xem case mẫu
              </button>
              <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-950 dark:text-purple-200">
                Pháp chế
              </span>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center p-6 text-xs text-[var(--text-muted)]">
              <Loader2 size={16} className="mr-2 animate-spin" /> Đang tải danh sách...
            </div>
          )}
          {error && (
            <p className="p-4 text-xs text-[var(--accent-error)]">Không tải được hộp thư.</p>
          )}
          {!isLoading && items.length === 0 && (
            <div className="p-6 text-center">
              <p className="text-sm text-[var(--text-secondary)]">Không có yêu cầu nào đang chờ ý kiến.</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Cán bộ xử lý sẽ gửi yêu cầu xin ý kiến khi gặp ambiguity pháp lý.
              </p>
            </div>
          )}
          <ul>
            {items.map((it) => {
              const sla = slaBadge(it.deadline);
              const urg = urgencyBadge(it.urgency);
              const active = selected?.request_id === it.request_id;
              return (
                <li key={it.request_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(it.request_id)}
                    className={cn(
                      "block w-full border-b border-[var(--border-subtle)] px-4 py-3 text-left transition-colors hover:bg-[var(--bg-surface-raised)]",
                      active && "bg-[var(--bg-surface-raised)]",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-mono text-[var(--text-secondary)]">
                        {it.case_code}
                      </span>
                      <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-medium", urg.cls)}>
                        {urg.label}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-[var(--text-primary)]">
                      {it.main_question || it.context_summary || "(không có nội dung)"}
                    </p>
                    <div className="mt-2 flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
                      <span className="truncate">{it.tthc_name || it.tthc_code}</span>
                      <span
                        className={cn(
                          "ml-auto flex items-center gap-1",
                          sla.tone === "danger" && "text-rose-600 dark:text-rose-400",
                          sla.tone === "warn" && "text-amber-600 dark:text-amber-400",
                        )}
                      >
                        <Clock size={11} /> {sla.label}
                      </span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </aside>

      {/* Right pane — detail + composer */}
      <section className="flex flex-1 flex-col overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        {!selected ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-[var(--text-muted)]">Chọn một yêu cầu bên trái để xem chi tiết.</p>
          </div>
        ) : (
          <>
            <header className="border-b border-[var(--border-subtle)] px-6 py-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h1 className="text-base font-semibold text-[var(--text-primary)]">
                    Xin ý kiến {selected.case_code}
                  </h1>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                    TTHC {selected.tthc_code} · {selected.tthc_name}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] dark:bg-slate-900">
                    {selected.applicant_name || "Chưa có người nộp"}
                  </span>
                  <span
                    className={cn(
                      "flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium",
                      slaBadge(selected.deadline).tone === "danger" &&
                        "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-200",
                      slaBadge(selected.deadline).tone === "warn" &&
                        "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
                      slaBadge(selected.deadline).tone === "ok" &&
                        "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200",
                    )}
                  >
                    <Clock size={11} /> {slaBadge(selected.deadline).label}
                  </span>
                </div>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid gap-4 lg:grid-cols-2">
                <article className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-app)] p-4">
                  <h3 className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
                    <FileText size={14} /> Bối cảnh
                  </h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--text-secondary)]">
                    {selected.context_summary || "Chưa có tóm tắt."}
                  </p>
                </article>
                <article className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-app)] p-4">
                  <h3 className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
                    <AlertTriangle size={14} /> Câu hỏi chính
                  </h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--text-primary)]">
                    {selected.main_question || "—"}
                  </p>
                  {selected.sub_questions && selected.sub_questions !== "[]" && (
                    <details className="mt-2 text-xs text-[var(--text-muted)]">
                      <summary className="cursor-pointer">Câu hỏi phụ</summary>
                      <pre className="mt-1 whitespace-pre-wrap text-[11px]">{selected.sub_questions}</pre>
                    </details>
                  )}
                </article>
              </div>

              {/* Precedent cases — similar previously-resolved TTHC cases */}
              <PrecedentCasesPanel caseId={selected.case_id ?? selected.case_code} />

              {/* Composer */}
              <section className="mt-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-app)] p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-[var(--text-primary)]">
                    Ý kiến của Phòng Pháp chế
                  </h3>
                  <button
                    type="button"
                    onClick={handleAiDraft}
                    disabled={aiDrafting}
                    className="flex items-center gap-1.5 rounded-md border border-purple-200 bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700 transition-colors hover:bg-purple-100 disabled:opacity-50 dark:border-purple-900 dark:bg-purple-950 dark:text-purple-200"
                  >
                    {aiDrafting ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                    AI gợi ý ý kiến
                  </button>
                </div>

                <div className="mt-3 flex gap-2">
                  {(
                    [
                      { v: "agree", label: "Đồng ý", icon: CheckCircle2, cls: "text-emerald-600" },
                      { v: "disagree", label: "Không đồng ý", icon: XCircle, cls: "text-rose-600" },
                      { v: "abstain", label: "Bảo lưu", icon: AlertTriangle, cls: "text-slate-600" },
                    ] as const
                  ).map(({ v, label, icon: Icon, cls }) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setStance(v)}
                      className={cn(
                        "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs transition-colors",
                        stance === v
                          ? "border-[var(--accent-primary)] bg-[var(--bg-surface-raised)] text-[var(--text-primary)]"
                          : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]",
                      )}
                    >
                      <Icon size={12} className={cls} /> {label}
                    </button>
                  ))}
                </div>

                <textarea
                  value={opinion}
                  onChange={(e) => setOpinion(e.target.value)}
                  rows={8}
                  placeholder="Soạn ý kiến chuyên môn... (bạn có thể bấm 'AI gợi ý' rồi chỉnh sửa)"
                  className="mt-3 w-full resize-y rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 text-sm text-[var(--text-primary)] outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                />

                <div className="mt-3 flex items-center justify-between">
                  <p className="text-[11px] text-[var(--text-muted)]">
                    Căn cứ NĐ 61/2018, phản hồi trước <strong>{selected.deadline || "(chưa đặt hạn)"}</strong>
                  </p>
                  <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={!opinion.trim() || submit.isPending}
                    className="flex items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-4 py-1.5 text-xs font-medium text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {submit.isPending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                    Gửi ý kiến
                  </button>
                </div>
              </section>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
