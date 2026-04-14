"use client";

import { useState, useEffect, useMemo } from "react";
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
import { GripVertical, Filter } from "lucide-react";
import type { CaseResponse } from "@/lib/types";

// TTHC name lookup for display
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

function SortableCaseCard({
  c,
  onClick,
}: {
  c: CaseResponse;
  onClick: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: c.case_id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={isDragging ? "opacity-30" : ""}
    >
      <div className="flex items-start gap-1">
        <button
          {...attributes}
          {...listeners}
          className="mt-3 cursor-grab rounded p-0.5 text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)] active:cursor-grabbing"
          aria-label={`Kéo hồ sơ ${c.code}`}
        >
          <GripVertical className="h-3 w-3" />
        </button>
        <div className="flex-1">
          <CaseCard
            caseId={c.code}
            title={c.applicant_name}
            tthcCode={c.tthc_code}
            tthcName={TTHC_NAMES[c.tthc_code] ?? c.tthc_code}
            status={c.status}
            classification="unclassified" /* TODO: derive from case data when available */
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
      </div>
    </div>
  );
}

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

  useEffect(() => {
    if (data?.items) {
      setLocalCases(data.items);
    }
  }, [data]);

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
    setActiveId(event.active.id as string);
  }

  async function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const caseId = active.id as string;
    const overId = over.id as string;

    // Determine target column
    let targetCol = COLUMNS.find((col) => col.id === overId);
    if (!targetCol) {
      // Dropped on a case card - find which column it belongs to
      const overCase = localCases.find((c) => c.case_id === overId);
      if (overCase) {
        targetCol = COLUMNS.find((col) =>
          col.statuses.includes(overCase.status),
        );
      }
    }
    if (!targetCol) return;

    // Find source column
    const draggedCase = localCases.find((c) => c.case_id === caseId);
    if (!draggedCase) return;
    const sourceCol = COLUMNS.find((col) =>
      col.statuses.includes(draggedCase.status),
    );
    if (sourceCol?.id === targetCol.id) return;

    // Optimistic update
    const newStatus = targetCol.statuses[0];
    const snapshot = [...localCases];
    setLocalCases((prev) =>
      prev.map((c) =>
        c.case_id === caseId ? { ...c, status: newStatus as CaseResponse["status"] } : c,
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Hồ sơ đến</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Quản lý và phân phối hồ sơ theo trạng thái xử lý. Kéo thả để chuyển trạng thái.
          </p>
        </div>
        <span className="text-sm text-[var(--text-muted)]">
          Tổng: {localCases.length} hồ sơ
        </span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-[var(--text-muted)]" />
        <input
          type="text"
          value={filterTTHC}
          onChange={(e) => setFilterTTHC(e.target.value)}
          placeholder="Lọc theo TTHC..."
          className="w-40 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-2 py-1 text-xs outline-none focus:border-[var(--accent-primary)]"
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
          <div className="flex gap-4 overflow-x-auto pb-4">
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
                          onClick={() =>
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
                  tthcName={TTHC_NAMES[activeCase.tthc_code] ?? activeCase.tthc_code}
                  status={activeCase.status}
                  classification="unclassified"
                  slaDeadline={
                    new Date(Date.now() + 7 * 86400000).toISOString()
                  }
                />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  );
}
