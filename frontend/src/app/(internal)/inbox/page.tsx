"use client";

import {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  type DragStartEvent,
  type DragEndEvent,
  useDroppable,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useCases } from "@/hooks/use-cases";
import { CaseCard } from "@/components/cases/case-card";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  GripVertical,
  Filter,
  CheckSquare,
  Square,
  ChevronDown,
  Loader2,
  X,
  Bot,
  UserCheck,
  Sparkles,
} from "lucide-react";
import { useArtifactPanelStore } from "@/lib/stores/artifact-panel-store";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { motion, AnimatePresence } from "framer-motion";
import type { CaseResponse } from "@/lib/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TTHC_NAMES: Record<string, string> = {
  "1.004415": "Cấp phép xây dựng",
  "1.000046": "GCN quyền sử dụng đất",
  "1.001757": "Đăng ký kinh doanh",
  "1.000122": "Lý lịch tư pháp",
  "2.002154": "Giấy phép môi trường",
};

const COLUMNS = [
  {
    id: "tiep_nhan",
    label: "Tiếp nhận",
    color: "var(--accent-info)",
    statuses: ["submitted", "classifying"],
  },
  {
    id: "dang_xu_ly",
    label: "Đang xử lý",
    color: "var(--accent-primary)",
    statuses: ["extracting", "gap_checking", "legal_review", "drafting"],
  },
  {
    id: "cho_y_kien",
    label: "Chờ ý kiến",
    color: "var(--accent-warning)",
    statuses: ["pending_supplement", "consultation", "leader_review"],
  },
  {
    id: "da_quyet_dinh",
    label: "Đã quyết định",
    color: "var(--accent-success)",
    statuses: ["approved", "rejected"],
  },
  {
    id: "tra_ket_qua",
    label: "Trả kết quả",
    color: "var(--text-muted)",
    statuses: ["published"],
  },
];

// ---------------------------------------------------------------------------
// SLA helpers
// ---------------------------------------------------------------------------

function getSlaRemainingMs(c: CaseResponse): number {
  if (!c.sla_days) return Infinity;
  return (
    new Date(c.submitted_at).getTime() +
    c.sla_days * 86400000 -
    Date.now()
  );
}

function isUrgent(c: CaseResponse): boolean {
  const rem = getSlaRemainingMs(c);
  return rem > 0 && rem < 24 * 3600 * 1000;
}

// ---------------------------------------------------------------------------
// AI assignment popover
// ---------------------------------------------------------------------------

interface AiAssignPopoverProps {
  caseCode: string;
  onClose: () => void;
  onConfirm: () => void;
}

function AiAssignPopover({
  caseCode,
  onClose,
  onConfirm,
}: AiAssignPopoverProps) {
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 1200);
    return () => clearTimeout(t);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92, y: 4 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.92, y: 4 }}
      transition={{ duration: 0.15 }}
      className="absolute left-0 top-full z-30 mt-1 w-72 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-3 shadow-xl"
    >
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold text-[var(--text-primary)]">
          AI gán chuyên viên
        </p>
        <button
          onClick={onClose}
          className="rounded p-0.5 text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)]"
          aria-label="Đóng"
        >
          <X className="h-3 w-3" />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-2">
          <Loader2 className="h-4 w-4 animate-spin text-[var(--accent-primary)]" />
          <p className="text-xs text-[var(--text-muted)]">
            Đang phân tích hồ sơ {caseCode}...
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-md bg-[var(--bg-surface-raised)] p-2.5">
            <p className="text-xs font-medium text-[var(--text-primary)]">
              Nguyễn Văn B
            </p>
            <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">
              Chuyên viên xây dựng · Phòng QLDT
            </p>
            <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--text-secondary)]">
              Lý do: Có kinh nghiệm 15 hồ sơ GPXD, tỷ lệ đúng hạn 97%, hiện xử lý ít hồ sơ nhất.
            </p>
          </div>
          <div className="mt-2 flex gap-2">
            <button
              onClick={onClose}
              className="flex-1 rounded-md border border-[var(--border-default)] py-1 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
            >
              Bỏ qua
            </button>
            <button
              onClick={onConfirm}
              className="flex flex-1 items-center justify-center gap-1 rounded-md bg-[var(--accent-primary)] py-1 text-xs font-medium text-white hover:opacity-90"
            >
              <UserCheck className="h-3 w-3" />
              Gán
            </button>
          </div>
        </>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Sortable card wrapper
// ---------------------------------------------------------------------------

function SortableCaseCard({
  c,
  onClick,
  selectMode,
  selected,
  onToggleSelect,
}: {
  c: CaseResponse;
  onClick: () => void;
  selectMode: boolean;
  selected: boolean;
  onToggleSelect: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: c.case_id });

  const setCase = useArtifactPanelStore((s) => s.setCase);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [showAiPopover, setShowAiPopover] = useState(false);
  const isFirstColumn =
    c.status === "submitted" || c.status === "classifying";
  const urgent = isUrgent(c);

  const handleMouseEnter = useCallback(() => {
    hoverTimerRef.current = setTimeout(() => {
      setCase(c.case_id);
    }, 500);
  }, [c.case_id, setCase]);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
  }, []);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={isDragging ? "opacity-30" : ""}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="relative flex items-start gap-1">
        {/* Select checkbox or grip */}
        {selectMode ? (
          <button
            onClick={onToggleSelect}
            className="mt-3 rounded p-0.5 text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)]"
            aria-label={selected ? "Bỏ chọn hồ sơ" : "Chọn hồ sơ"}
            aria-pressed={selected}
          >
            {selected ? (
              <CheckSquare className="h-3.5 w-3.5 text-[var(--accent-primary)]" />
            ) : (
              <Square className="h-3.5 w-3.5" />
            )}
          </button>
        ) : (
          <button
            {...attributes}
            {...listeners}
            className="mt-3 cursor-grab rounded p-0.5 text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)] active:cursor-grabbing"
            aria-label={`Kéo hồ sơ ${c.code}`}
          >
            <GripVertical className="h-3 w-3" />
          </button>
        )}

        <div className="relative flex-1">
          {/* SLA urgent pulsing ring */}
          {urgent && (
            <motion.div
              className="pointer-events-none absolute -inset-0.5 z-0 rounded-lg"
              animate={{
                boxShadow: [
                  "0 0 0 0 rgba(239,68,68,0)",
                  "0 0 0 3px rgba(239,68,68,0.35)",
                  "0 0 0 0 rgba(239,68,68,0)",
                ],
              }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          )}
          <div className="relative z-10">
            <CaseCard
              caseId={c.code}
              title={c.applicant_name}
              tthcCode={c.tthc_code}
              tthcName={TTHC_NAMES[c.tthc_code] ?? c.tthc_code}
              status={c.status}
              classification="unclassified"
              slaDeadline={
                c.sla_days
                  ? new Date(
                      new Date(c.submitted_at).getTime() +
                        c.sla_days * 86400000,
                    ).toISOString()
                  : new Date(Date.now() + 7 * 86400000).toISOString()
              }
              onClick={onClick}
            />
          </div>

          {/* AI assign button — only in "Tiếp nhận" column, not in select mode */}
          {isFirstColumn && !selectMode && (
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowAiPopover((v) => !v);
                }}
                className="mt-1 flex w-full items-center justify-center gap-1 rounded-b-md border border-t-0 border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] py-1 text-[10px] font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--accent-primary)]/5 hover:text-[var(--accent-primary)]"
                aria-label="AI gán chuyên viên"
                aria-expanded={showAiPopover}
              >
                <Bot className="h-3 w-3" />
                AI gán chuyên viên
              </button>

              <AnimatePresence>
                {showAiPopover && (
                  <AiAssignPopover
                    caseCode={c.code}
                    onClose={() => setShowAiPopover(false)}
                    onConfirm={() => {
                      setShowAiPopover(false);
                      toast.success(
                        `Đã gán hồ sơ ${c.code} cho Nguyễn Văn B`,
                      );
                    }}
                  />
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Droppable column
// ---------------------------------------------------------------------------

function DroppableColumn({
  column,
  children,
}: {
  column: (typeof COLUMNS)[number];
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <div
      ref={setNodeRef}
      className={`min-w-[280px] flex-shrink-0 ${isOver ? "ring-1 ring-inset ring-[var(--accent-primary)]/40" : ""}`}
      aria-label={`Cột ${column.label}`}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Floating bulk action bar
// ---------------------------------------------------------------------------

function BulkActionBar({
  count,
  onMove,
  onCancel,
}: {
  count: number;
  onMove: (colId: string) => void;
  onCancel: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 24 }}
      className="fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2.5 shadow-2xl"
    >
      <span className="text-sm font-medium text-[var(--text-primary)]">
        Đã chọn{" "}
        <span className="font-bold text-[var(--accent-primary)]">{count}</span>{" "}
        hồ sơ
      </span>

      <div className="relative">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
          aria-haspopup="listbox"
          aria-expanded={open}
        >
          Chuyển {count} case sang →
          <ChevronDown className="h-3.5 w-3.5" />
        </button>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="absolute bottom-full left-0 mb-1 w-48 overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-lg"
              role="listbox"
            >
              {COLUMNS.map((col) => (
                <button
                  key={col.id}
                  role="option"
                  onClick={() => {
                    setOpen(false);
                    onMove(col.id);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-left hover:bg-[var(--bg-surface-raised)]"
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ background: col.color }}
                  />
                  {col.label}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <button
        onClick={onCancel}
        className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
        aria-label="Hủy chọn nhiều"
      >
        Hủy
      </button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DepartmentInbox() {
  const { data, isLoading } = useCases();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [localCases, setLocalCases] = useState<CaseResponse[]>([]);
  const [filterTTHC, setFilterTTHC] = useState("");
  const [filterSLA, setFilterSLA] = useState<"all" | "urgent" | "overdue">(
    "all",
  );
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (data?.items) {
      setLocalCases(data.items);
    }
  }, [data]);

  // Exit select mode on ESC
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && selectMode) {
        setSelectMode(false);
        setSelectedIds(new Set());
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectMode]);

  const filteredCases = useMemo(() => {
    let cases = localCases;
    if (filterTTHC) {
      cases = cases.filter((c) =>
        c.tthc_code.toLowerCase().includes(filterTTHC.toLowerCase()),
      );
    }
    if (filterSLA === "overdue") {
      cases = cases.filter((c) => c.is_overdue);
    } else if (filterSLA === "urgent") {
      cases = cases.filter((c) => {
        if (!c.sla_days) return false;
        const deadline =
          new Date(c.submitted_at).getTime() + c.sla_days * 86400000;
        const remaining = deadline - Date.now();
        return remaining > 0 && remaining < 3 * 86400000;
      });
    }
    return cases;
  }, [localCases, filterTTHC, filterSLA]);

  function getCasesForColumn(statuses: string[]): CaseResponse[] {
    return filteredCases.filter((c) => statuses.includes(c.status));
  }

  const activeCase = localCases.find((c) => c.case_id === activeId);

  function handleDragStart(event: DragStartEvent) {
    if (selectMode) return;
    setActiveId(event.active.id as string);
  }

  async function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const caseId = active.id as string;
    const overId = over.id as string;

    let targetCol = COLUMNS.find((col) => col.id === overId);
    if (!targetCol) {
      const overCase = localCases.find((c) => c.case_id === overId);
      if (overCase) {
        targetCol = COLUMNS.find((col) =>
          col.statuses.includes(overCase.status),
        );
      }
    }
    if (!targetCol) return;

    const draggedCase = localCases.find((c) => c.case_id === caseId);
    if (!draggedCase) return;
    const sourceCol = COLUMNS.find((col) =>
      col.statuses.includes(draggedCase.status),
    );
    if (sourceCol?.id === targetCol.id) return;

    const newStatus = targetCol.statuses[0];
    const snapshot = [...localCases];
    setLocalCases((prev) =>
      prev.map((c) =>
        c.case_id === caseId
          ? { ...c, status: newStatus as CaseResponse["status"] }
          : c,
      ),
    );

    try {
      await apiClient.patch(`/api/cases/${caseId}`, { status: newStatus });
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      toast.success(`Đã chuyển hồ sơ sang "${targetCol.label}"`);
    } catch {
      setLocalCases(snapshot);
      toast.error("Không thể cập nhật trạng thái hồ sơ");
    }
  }

  // Bulk move selected cases to a target column
  async function handleBulkMove(colId: string) {
    const targetCol = COLUMNS.find((c) => c.id === colId);
    if (!targetCol) return;
    const newStatus = targetCol.statuses[0];

    const ids = Array.from(selectedIds);
    const snapshot = [...localCases];

    setLocalCases((prev) =>
      prev.map((c) =>
        selectedIds.has(c.case_id)
          ? { ...c, status: newStatus as CaseResponse["status"] }
          : c,
      ),
    );
    setSelectMode(false);
    setSelectedIds(new Set());

    let failed = 0;
    await Promise.all(
      ids.map(async (id) => {
        try {
          await apiClient.patch(`/api/cases/${id}`, { status: newStatus });
        } catch {
          failed++;
        }
      }),
    );

    if (failed > 0) {
      setLocalCases(snapshot);
      toast.error(`Không thể cập nhật ${failed} hồ sơ`);
    } else {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      toast.success(
        `Đã chuyển ${ids.length} hồ sơ sang "${targetCol.label}"`,
      );
    }
  }

  function toggleSelect(caseId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(caseId)) next.delete(caseId);
      else next.add(caseId);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      {/* Bulk action floating bar */}
      <AnimatePresence>
        {selectMode && selectedIds.size > 0 && (
          <BulkActionBar
            count={selectedIds.size}
            onMove={handleBulkMove}
            onCancel={() => {
              setSelectMode(false);
              setSelectedIds(new Set());
            }}
          />
        )}
      </AnimatePresence>

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Hồ sơ đến</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Quản lý và phân phối hồ sơ theo trạng thái xử lý. Kéo thả để
            chuyển trạng thái.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Multi-select toggle */}
          <button
            onClick={() => {
              setSelectMode((v) => !v);
              if (selectMode) setSelectedIds(new Set());
            }}
            aria-pressed={selectMode}
            className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
              selectMode
                ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                : "border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
            }`}
          >
            <CheckSquare className="h-3.5 w-3.5" />
            {selectMode ? "Đang chọn nhiều" : "Chọn nhiều"}
          </button>

          <span className="text-sm text-[var(--text-muted)]">
            Tổng: {localCases.length} hồ sơ
          </span>
          <button
            type="button"
            onClick={() => router.push("/trace/CASE-2026-0001")}
            className="flex items-center gap-1.5 rounded-md border border-purple-300 bg-gradient-to-r from-purple-600 to-violet-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
            title="Mở hồ sơ CPXD mẫu có gap PCCC"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Xem case mẫu
          </button>
          <OnboardingTour tourId="officer-inbox" />
        </div>
      </div>

      {/* Hint banner */}
      <HelpHintBanner id="inbox-kanban-drag" variant="tip">
        Dùng nút{" "}
        <span className="font-mono font-bold">≡</span> bên trái mỗi thẻ để
        kéo thả hồ sơ giữa các cột và chuyển trạng thái xử lý.
      </HelpHintBanner>

      {/* Filters */}
      <div className="flex items-center gap-3" data-tour="inbox-filter">
        <Filter className="h-4 w-4 text-[var(--text-muted)]" />
        <input
          type="text"
          value={filterTTHC}
          onChange={(e) => setFilterTTHC(e.target.value)}
          placeholder="Lọc theo TTHC..."
          aria-label="Lọc theo loại thủ tục hành chính"
          className="w-40 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-2 py-1 text-xs outline-none focus:border-[var(--accent-primary)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        />
        <div className="flex gap-1">
          {(
            [
              { key: "all", label: "Tất cả" },
              { key: "urgent", label: "Sắp hạn" },
              { key: "overdue", label: "Quá hạn" },
            ] as const
          ).map((f) => (
            <button
              key={f.key}
              onClick={() => setFilterSLA(f.key)}
              aria-pressed={filterSLA === f.key}
              className={`rounded-md px-2 py-1 text-xs transition-colors ${
                filterSLA === f.key
                  ? "bg-[var(--accent-primary)] text-white"
                  : "bg-[var(--bg-surface-raised)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map((col) => (
            <div key={col.id} className="min-w-[280px] flex-shrink-0">
              <div className="h-8 animate-pulse rounded bg-[var(--bg-surface-raised)]" />
              <div className="mt-3 space-y-2">
                {[...Array(3)].map((_, i) => (
                  <div
                    key={i}
                    className="h-24 animate-pulse rounded-lg bg-[var(--bg-surface)]"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <DndContext
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div
            className="flex gap-4 overflow-x-auto pb-4"
            data-tour="inbox-kanban"
          >
            {COLUMNS.map((col) => {
              const colCases = getCasesForColumn(col.statuses);
              return (
                <DroppableColumn key={col.id} column={col}>
                  {/* Column header */}
                  <div className="mb-3 flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{ background: col.color }}
                    />
                    <h3 className="text-sm font-semibold">{col.label}</h3>
                    <span className="rounded-full bg-[var(--bg-surface-raised)] px-2 text-[10px]">
                      {colCases.length}
                    </span>
                  </div>

                  <SortableContext
                    items={colCases.map((c) => c.case_id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="min-h-[120px] space-y-2" role="list">
                      {colCases.map((c) => (
                        <SortableCaseCard
                          key={c.case_id}
                          c={c}
                          selectMode={selectMode}
                          selected={selectedIds.has(c.case_id)}
                          onToggleSelect={() => toggleSelect(c.case_id)}
                          onClick={() =>
                            !selectMode &&
                            router.push(`/compliance/${c.case_id}`)
                          }
                        />
                      ))}
                      {colCases.length === 0 && (
                        <div className="rounded-md border border-dashed border-[var(--border-subtle)] p-4 text-center text-xs text-[var(--text-muted)]">
                          Không có hồ sơ
                        </div>
                      )}
                    </div>
                  </SortableContext>
                </DroppableColumn>
              );
            })}
          </div>

          {/* Drag overlay ghost */}
          <DragOverlay dropAnimation={null}>
            {activeCase && (
              <div className="w-[280px] rotate-1 opacity-90 shadow-2xl">
                <CaseCard
                  caseId={activeCase.code}
                  title={activeCase.applicant_name}
                  tthcCode={activeCase.tthc_code}
                  tthcName={
                    TTHC_NAMES[activeCase.tthc_code] ?? activeCase.tthc_code
                  }
                  status={activeCase.status}
                  classification="unclassified"
                  slaDeadline={new Date(
                    Date.now() + 7 * 86400000,
                  ).toISOString()}
                />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  );
}
