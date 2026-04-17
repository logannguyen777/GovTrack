"use client";

import { useCallback, useState } from "react";
import { useWSTopic, useWSConnection } from "@/hooks/use-ws";
import { useAuditEvents } from "@/hooks/use-audit";
import { RedactedField } from "@/components/ui/redacted-field";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { apiClient } from "@/lib/api";
import type { WSMessage, AuditEventResponse } from "@/lib/types";
import { toast } from "sonner";
import { Shield, AlertTriangle, Eye, Download, ChevronDown } from "lucide-react";
import { HELP_CONTENT } from "@/lib/help-content";
import { motion, AnimatePresence } from "framer-motion";

// ---------------------------------------------------------------------------
// 3-view property mask data
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// 3-view demo fixtures — scoped inside ThreeViewToggle (not module-level)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Masking helpers
// ---------------------------------------------------------------------------

type ViewLevel = "L0" | "L1" | "L3";

function maskNationalId(id: string, level: ViewLevel): string {
  if (level === "L3") return id;
  if (level === "L1") return id.slice(0, 4) + "***" + id.slice(-4);
  return "[REDACTED]";
}

function maskPhone(phone: string, level: ViewLevel): string {
  if (level === "L3") return phone;
  if (level === "L1") return phone.slice(0, 4) + "***" + phone.slice(-4);
  return "***" + phone.slice(-4);
}

function maskAddress(address: string, level: ViewLevel): string {
  if (level === "L3") return address;
  if (level === "L1") return "[Một phần địa chỉ — Quận/Huyện]";
  return "[CLASSIFIED]";
}

function maskEmail(email: string, level: ViewLevel): string {
  if (level === "L3") return email;
  if (level === "L1") {
    const [local, domain] = email.split("@");
    return local.slice(0, 2) + "***@" + domain;
  }
  return "[CLASSIFIED]";
}

// ---------------------------------------------------------------------------
// 3-View Pane component
// ---------------------------------------------------------------------------

const LEVEL_CONFIG: Record<ViewLevel, { label: string; role: string; clearance: number; color: string; borderColor: string; bgClass: string }> = {
  L0: {
    label: "Cán bộ tiếp nhận",
    role: "staff_intake · Clearance 0",
    clearance: 0,
    color: "text-emerald-700 dark:text-emerald-300",
    borderColor: "border-emerald-300 dark:border-emerald-700",
    bgClass: "bg-emerald-50/60 dark:bg-emerald-950/20",
  },
  L1: {
    label: "Chuyên viên khác Sở",
    role: "staff_processor · Clearance 1",
    clearance: 1,
    color: "text-amber-700 dark:text-amber-300",
    borderColor: "border-amber-300 dark:border-amber-700",
    bgClass: "bg-amber-50/60 dark:bg-amber-950/20",
  },
  L3: {
    label: "Lãnh đạo",
    role: "leader · Clearance 3",
    clearance: 3,
    color: "text-blue-700 dark:text-blue-300",
    borderColor: "border-blue-300 dark:border-blue-700",
    bgClass: "bg-blue-50/60 dark:bg-blue-950/20",
  },
};

function ApplicantViewPane({ level, applicant }: { level: ViewLevel; applicant: DemoCaseApplicant }) {
  const cfg = LEVEL_CONFIG[level];
  const isRevealed = level === "L3";

  const rows: Array<{ label: string; value: string }> = [
    { label: "Họ và tên", value: applicant.name }, // name always visible
    { label: "CCCD/CMND", value: maskNationalId(applicant.national_id, level) },
    { label: "Số điện thoại", value: maskPhone(applicant.phone, level) },
    { label: "Địa chỉ", value: maskAddress(applicant.address, level) },
    { label: "Ngày sinh", value: level === "L0" ? "[REDACTED]" : applicant.dob },
    { label: "Email", value: maskEmail(applicant.email, level) },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
      className={`rounded-lg border-2 ${cfg.borderColor} ${cfg.bgClass} overflow-hidden`}
    >
      {/* Header */}
      <div className={`px-3 py-2 border-b ${cfg.borderColor}`}>
        <p className={`text-xs font-bold ${cfg.color}`}>{cfg.label}</p>
        <p className="text-[10px] text-[var(--text-muted)] font-mono">{cfg.role}</p>
        <div className="mt-1 flex gap-1">
          {[0, 1, 2, 3].map((n) => (
            <div
              key={n}
              className={`h-1.5 w-5 rounded-full ${n <= cfg.clearance ? cfg.borderColor.replace("border", "bg") : "bg-[var(--bg-subtle)]"}`}
              title={`Clearance level ${n}`}
            />
          ))}
        </div>
      </div>

      {/* Fields */}
      <div className="p-3 space-y-2">
        {rows.map(({ label, value }) => (
          <div key={label}>
            <p className="text-[10px] text-[var(--text-muted)]">{label}</p>
            {label === "CCCD/CMND" ? (
              <RedactedField value={applicant.national_id} isRevealed={isRevealed} />
            ) : value === "[REDACTED]" || value === "[CLASSIFIED]" || value === "[Một phần địa chỉ — Quận/Huyện]" ? (
              <span
                className="inline-flex items-center rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wider select-none"
                style={{ backgroundColor: "var(--text-primary)", color: "var(--bg-surface)" }}
              >
                {value}
              </span>
            ) : (
              <p className="text-xs font-medium text-[var(--text-primary)] truncate" title={value}>
                {value}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Permission note */}
      <div className={`px-3 py-1.5 border-t ${cfg.borderColor} text-[10px] ${cfg.color} font-mono`}>
        {level === "L0" && "property_mask: national_id=REDACT, address=CLASSIFIED"}
        {level === "L1" && "property_mask: national_id=PARTIAL, address=PARTIAL"}
        {level === "L3" && "property_mask: none — full_access"}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// 3-View Toggle section
// ---------------------------------------------------------------------------

// Demo fixtures for the 3-view PermittedGremlinClient security demo
interface DemoCaseApplicant {
  name: string;
  national_id: string;
  phone: string;
  address: string;
  dob: string;
  email: string;
}

const SECURITY_CASES_FIXTURE = [
  { id: "HS-2026-001", label: "HS-2026-001 · GPXD Quận 1" },
  { id: "HS-2026-002", label: "HS-2026-002 · Đăng ký kinh doanh" },
  { id: "HS-2026-003", label: "HS-2026-003 · Cấp GCN đất ở" },
  { id: "HS-2026-004", label: "HS-2026-004 · Chứng thực bản sao" },
  { id: "HS-2026-005", label: "HS-2026-005 · Lý lịch tư pháp" },
] as const;

const SECURITY_APPLICANTS_FIXTURE: Record<string, DemoCaseApplicant> = {
  "HS-2026-001": { name: "Nguyễn Văn Minh",   national_id: "079201001234", phone: "0912345678", address: "12 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM", dob: "15/03/1985", email: "nguyenvanminh@gmail.com" },
  "HS-2026-002": { name: "Trần Thị Bích Lan",  national_id: "031297002567", phone: "0987654321", address: "45 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP.HCM", dob: "22/07/1990", email: "tranbichlan@email.vn" },
  "HS-2026-003": { name: "Lê Quốc Hùng",      national_id: "070198003891", phone: "0908112233", address: "78 Điện Biên Phủ, Phường 15, Bình Thạnh, TP.HCM", dob: "03/11/1979", email: "lequochung@vnpt.vn" },
  "HS-2026-004": { name: "Phạm Thị Thu Hà",   national_id: "001285004412", phone: "0936778899", address: "23 Hoàng Diệu, Phường 13, Quận 4, TP.HCM", dob: "19/06/1988", email: "phamthuthuha@yahoo.com" },
  "HS-2026-005": { name: "Võ Thanh Tùng",     national_id: "052190005234", phone: "0918223344", address: "56 Cách Mạng Tháng 8, Phường 3, Quận 3, TP.HCM", dob: "30/01/1982", email: "vothanhtung@fpt.vn" },
};

function ThreeViewToggle() {
  const [selectedCase, setSelectedCase] = useState<string>(SECURITY_CASES_FIXTURE[0].id);
  const [open, setOpen] = useState(true);

  const applicant = SECURITY_APPLICANTS_FIXTURE[selectedCase] ?? SECURITY_APPLICANTS_FIXTURE["HS-2026-001"];

  return (
    <div className="rounded-lg border-2 border-[var(--accent-primary)]/30 bg-[var(--bg-surface)] overflow-hidden">
      {/* Toggle header */}
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] text-left"
        aria-expanded={open}
        aria-controls="three-view-panel"
      >
        <div className="flex items-center gap-2">
          <Eye className="h-4 w-4 text-[var(--accent-primary)]" aria-hidden="true" />
          <span className="text-sm font-bold">3 góc nhìn — Cùng một hồ sơ, khác mức phân quyền</span>
          <span className="rounded-full bg-[var(--accent-primary)]/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--accent-primary)]">
            Demo PermittedGremlinClient
          </span>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-[var(--text-muted)] transition-transform duration-250 ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id="three-view-panel"
            key="panel"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-[var(--border-subtle)] p-4 space-y-4">
              {/* Case selector */}
              <div className="flex items-center gap-3">
                <label htmlFor="demo-case-select" className="text-xs font-medium text-[var(--text-secondary)] whitespace-nowrap">
                  Chọn hồ sơ:
                </label>
                <select
                  id="demo-case-select"
                  value={selectedCase}
                  onChange={(e) => setSelectedCase(e.target.value)}
                  className="flex-1 max-w-xs rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] px-2 py-1.5 text-xs outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
                >
                  {SECURITY_CASES_FIXTURE.map((c) => (
                    <option key={c.id} value={c.id}>{c.label}</option>
                  ))}
                </select>
                <p className="text-[10px] text-[var(--text-muted)] italic hidden sm:block">
                  Mỗi cột ứng với một vai trò / clearance level khác nhau.
                </p>
              </div>

              {/* 3 panes */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {(["L0", "L1", "L3"] as ViewLevel[]).map((level) => (
                  <ApplicantViewPane key={level} level={level} applicant={applicant} />
                ))}
              </div>

              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                <strong>PermittedGremlinClient</strong> áp dụng 3 tầng kiểm soát: SDK Guard (Tier 1) →
                RBAC theo vai trò (Tier 2) → Property Mask theo clearance level (Tier 3).
                Dữ liệu phía trên được tự động che khuất trước khi trả về client.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CSV Export
// ---------------------------------------------------------------------------

function exportAuditCSV(events: AuditEventResponse[]) {
  if (events.length === 0) {
    toast.info("Không có sự kiện nào để xuất.");
    return;
  }

  const headers = ["Thời gian", "Loại sự kiện", "Người thực hiện", "Đối tượng", "ID đối tượng", "Hồ sơ", "Chi tiết"];

  const rows = events.map((e) => [
    new Date(e.created_at).toLocaleString("vi-VN"),
    e.event_type ?? "",
    e.actor_name ?? "system",
    e.target_type ?? "",
    e.target_id ?? "",
    e.case_id ?? "",
    e.details ? JSON.stringify(e.details).replace(/"/g, "'") : "",
  ]);

  const csvContent = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    .join("\n");

  const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `govflow-audit-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  toast.success(`Đã xuất ${events.length} sự kiện ra CSV.`);
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SecurityConsole() {
  const [liveEvents, setLiveEvents] = useState<AuditEventResponse[]>([]);
  const [elevationActive, setElevationActive] = useState(false);
  const [triggeringScene, setTriggeringScene] = useState<string | null>(null);

  // Filters
  const [filterActor, setFilterActor] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  const { data: historicalEvents, error: auditError, refetch: refetchAudit } = useAuditEvents({ limit: 100 });

  useWSConnection();

  const handleAudit = useCallback((msg: WSMessage) => {
    const event = msg.data as AuditEventResponse;
    setLiveEvents((prev) => [event, ...prev].slice(0, 200));
  }, []);

  useWSTopic("security:audit", handleAudit);

  const allEvents = [
    ...liveEvents,
    ...(historicalEvents ?? []).filter(
      (h) => !liveEvents.some((l) => l.id === h.id),
    ),
  ];

  // Apply client-side filters
  const filteredEvents = allEvents.filter((e) => {
    if (
      filterActor &&
      !(e.actor_name ?? "").toLowerCase().includes(filterActor.toLowerCase())
    )
      return false;
    if (
      filterAction &&
      !(e.event_type ?? "").toLowerCase().includes(filterAction.toLowerCase())
    )
      return false;
    if (filterDateFrom) {
      const evDate = new Date(e.created_at);
      const from = new Date(filterDateFrom + "T00:00:00");
      if (evDate < from) return false;
    }
    if (filterDateTo) {
      const evDate = new Date(e.created_at);
      const to = new Date(filterDateTo + "T23:59:59");
      if (evDate > to) return false;
    }
    return true;
  });

  async function triggerScene(scene: string) {
    setTriggeringScene(scene);
    try {
      await apiClient.post(`/api/demo/permissions/${scene}`);
      toast.success(`Đã kích hoạt kịch bản: ${scene}`);
    } catch {
      toast.error("Demo endpoint không khả dụng");
    } finally {
      setTriggeringScene(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6 text-[var(--accent-primary)]" />
          <h1 className="text-2xl font-bold">Trung tâm bảo mật</h1>
        </div>
        <OnboardingTour tourId="leader-dashboard" showButton={true} />
      </div>

      <HelpHintBanner id="security-3-tier" variant="info">
        {HELP_CONTENT["security-3-tier"]}
      </HelpHintBanner>

      {/* 3-view toggle section — hero demo above scenarios */}
      <ThreeViewToggle />

      <div className="grid grid-cols-3 gap-4">
        {/* Live audit log */}
        <div className="col-span-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">
              Nhật ký kiểm tra (Live)
              <span className="ml-2 font-mono text-[10px] text-[var(--text-muted)]">
                {filteredEvents.length}/{allEvents.length}
              </span>
            </h3>
            <div className="flex items-center gap-2">
              {/* Export CSV button */}
              <button
                type="button"
                onClick={() => exportAuditCSV(filteredEvents)}
                className="flex items-center gap-1.5 rounded border border-[var(--border-default)] px-2 py-1 text-[10px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
                aria-label="Xuất nhật ký kiểm tra ra CSV"
              >
                <Download className="h-3 w-3" aria-hidden="true" />
                Xuất CSV
              </button>
              {auditError && (
                <button
                  onClick={() => refetchAudit()}
                  className="flex items-center gap-1 rounded border border-[var(--border-default)] px-2 py-1 text-[10px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
                >
                  <AlertTriangle className="h-3 w-3 text-[var(--accent-error)]" />
                  Thử lại
                </button>
              )}
            </div>
          </div>

          {/* Filter bar */}
          <div className="mb-3 flex flex-wrap gap-2">
            <input
              type="text"
              value={filterActor}
              onChange={(e) => setFilterActor(e.target.value)}
              placeholder="Lọc theo actor..."
              className="h-7 rounded border border-[var(--border-default)] bg-[var(--bg-canvas)] px-2 text-[11px] outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
              aria-label="Lọc theo actor"
            />
            <input
              type="text"
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              placeholder="Loại sự kiện..."
              className="h-7 rounded border border-[var(--border-default)] bg-[var(--bg-canvas)] px-2 text-[11px] outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
              aria-label="Lọc theo loại sự kiện"
            />
            <input
              type="date"
              value={filterDateFrom}
              onChange={(e) => setFilterDateFrom(e.target.value)}
              className="h-7 rounded border border-[var(--border-default)] bg-[var(--bg-canvas)] px-2 text-[11px] outline-none focus:border-[var(--accent-primary)]"
              aria-label="Từ ngày"
              title="Từ ngày"
            />
            <input
              type="date"
              value={filterDateTo}
              onChange={(e) => setFilterDateTo(e.target.value)}
              className="h-7 rounded border border-[var(--border-default)] bg-[var(--bg-canvas)] px-2 text-[11px] outline-none focus:border-[var(--accent-primary)]"
              aria-label="Đến ngày"
              title="Đến ngày"
            />
            {(filterActor || filterAction || filterDateFrom || filterDateTo) && (
              <button
                type="button"
                onClick={() => {
                  setFilterActor("");
                  setFilterAction("");
                  setFilterDateFrom("");
                  setFilterDateTo("");
                }}
                className="h-7 rounded border border-[var(--border-default)] px-2 text-[11px] text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)]"
              >
                Xoá bộ lọc
              </button>
            )}
          </div>

          {auditError ? (
            <div className="flex items-center gap-3 rounded-md border border-[var(--border-subtle)] p-4">
              <AlertTriangle className="h-5 w-5 shrink-0 text-[var(--accent-warning)]" />
              <div>
                <p className="text-sm font-semibold">Nhật ký kiểm tra</p>
                <p className="text-xs text-[var(--text-muted)]">
                  {String((auditError as Error).message ?? "").includes("403")
                    ? "Bạn cần quyền Quản trị viên hoặc Lãnh đạo để xem nhật ký kiểm tra."
                    : "Không thể tải nhật ký. Vui lòng thử lại."}
                </p>
              </div>
            </div>
          ) : (
            <div className="max-h-[500px] space-y-1 overflow-auto font-mono text-xs">
              {filteredEvents.length === 0 && allEvents.length === 0 && (
                <p className="py-4 text-center text-[var(--text-muted)]">
                  Chưa có sự kiện audit nào.
                </p>
              )}
              {filteredEvents.length === 0 && allEvents.length > 0 && (
                <p className="py-4 text-center text-[var(--text-muted)]">
                  Không có sự kiện khớp với bộ lọc.
                </p>
              )}
              {filteredEvents.map((event, i) => {
                const isDeny =
                  event.event_type === "DENY" ||
                  event.event_type?.toLowerCase().includes("deny") ||
                  event.event_type === "permission_denied";
                return (
                  <div
                    key={event.id || i}
                    className={`flex gap-2 rounded px-2 py-1 ${
                      isDeny
                        ? "animate-deny-flash text-[var(--accent-error)]"
                        : "text-[var(--text-secondary)]"
                    }`}
                  >
                    <span className="w-20 shrink-0 text-[var(--text-muted)]">
                      {new Date(event.created_at).toLocaleTimeString("vi-VN")}
                    </span>
                    <span className="w-16 shrink-0 font-bold">
                      {event.event_type}
                    </span>
                    <span className="w-28 shrink-0">
                      {event.actor_name ?? "system"}
                    </span>
                    <span className="truncate">
                      {event.target_type}:{event.target_id}{" "}
                      {event.details
                        ? JSON.stringify(event.details).slice(0, 80)
                        : ""}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Demo controls */}
        <div className="space-y-4" data-tour="security-3-tier">
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="mb-3 text-sm font-semibold">Kiểm tra phân quyền</h3>
            <div className="space-y-2">
              <button
                onClick={() => triggerScene("scene-a/sdk-guard-rejection")}
                disabled={triggeringScene !== null}
                className="flex w-full items-center gap-2 rounded-md border border-[var(--border-default)] px-3 py-2 text-left text-xs transition-colors hover:bg-[var(--bg-surface-raised)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {triggeringScene === "scene-a/sdk-guard-rejection" ? (
                  <span className="h-3 w-3 animate-spin rounded-full border border-[var(--accent-warning)] border-t-transparent" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-[var(--accent-warning)]" />
                )}
                Kịch bản A: Chặn truy cập thuộc tính cấm
              </button>
              <button
                onClick={() => triggerScene("scene-b/rbac-rejection")}
                disabled={triggeringScene !== null}
                className="flex w-full items-center gap-2 rounded-md border border-[var(--border-default)] px-3 py-2 text-left text-xs transition-colors hover:bg-[var(--bg-surface-raised)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {triggeringScene === "scene-b/rbac-rejection" ? (
                  <span className="h-3 w-3 animate-spin rounded-full border border-[var(--accent-error)] border-t-transparent" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-[var(--accent-error)]" />
                )}
                Kịch bản B: Chặn do phân quyền vai trò
              </button>
              <button
                onClick={() => setElevationActive(!elevationActive)}
                className="flex w-full items-center gap-2 rounded-md border border-[var(--border-default)] px-3 py-2 text-left text-xs transition-colors hover:bg-[var(--bg-surface-raised)]"
              >
                <Eye className="h-3 w-3 text-[var(--accent-success)]" />
                Kịch bản C: Nâng cấp mức bảo mật{" "}
                {elevationActive ? "(BẬT)" : "(TẮT)"}
              </button>
            </div>
          </div>

          {/* Classification distribution */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="mb-3 text-sm font-semibold">Phân bổ phân loại</h3>
            <div className="space-y-2 text-xs">
              <ClassBar label="Không mật" pct={70} color="var(--classification-unclassified)" />
              <ClassBar label="Mật" pct={20} color="var(--classification-confidential)" />
              <ClassBar label="Tối mật" pct={8} color="var(--classification-secret)" />
              <ClassBar label="Tuyệt mật" pct={2} color="var(--classification-top-secret)" />
            </div>
          </div>

          {/* Denial heatmap */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="mb-3 text-sm font-semibold">Từ chối theo giờ</h3>
            <DenialHeatmap />
          </div>
        </div>
      </div>

      {/* Clearance Elevation Demo */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 className="mb-3 text-sm font-semibold">
          Mô phỏng nâng cấp bảo mật
        </h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-xs text-[var(--text-muted)]">CCCD</p>
            <RedactedField value="079201001234" isRevealed={elevationActive} />
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)]">Địa chỉ</p>
            <RedactedField
              value="12 Lê Lợi, Quận 1, TP.HCM"
              isRevealed={elevationActive}
            />
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)]">Tài khoản</p>
            <RedactedField
              value="VCB 1234567890"
              isRevealed={elevationActive}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function ClassBar({
  label,
  pct,
  color,
}: {
  label: string;
  pct: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-16 text-[var(--text-secondary)]">{label}</span>
      <div className="flex-1">
        <div
          className="h-4 rounded-sm"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-8 text-right font-mono">{pct}%</span>
    </div>
  );
}

const AGENTS_SHORT = ["Plan", "Doc", "Class", "Comp", "Legal", "Route", "Cons", "Summ", "Draft", "Sec"];
const HOURS = ["00", "04", "08", "12", "16", "20"];

function DenialHeatmap() {
  // Deterministic denial counts for demo
  const data = AGENTS_SHORT.map((_, ai) =>
    HOURS.map((_, hi) => {
      const v = (ai * 7 + hi * 13 + 3) % 12;
      return v < 4 ? 0 : v < 7 ? 1 : v < 10 ? 2 : 3;
    }),
  );

  function cellColor(count: number) {
    if (count === 0) return "var(--bg-surface-raised)";
    if (count === 1) return "var(--accent-warning)";
    if (count === 2) return "var(--accent-error)";
    return "var(--classification-top-secret)";
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[10px]">
        <thead>
          <tr>
            <th className="pb-1 text-left text-[var(--text-muted)]" />
            {HOURS.map((h) => (
              <th key={h} className="pb-1 text-center text-[var(--text-muted)]">
                {h}h
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {AGENTS_SHORT.map((agent, ai) => (
            <tr key={agent}>
              <td className="pr-2 py-0.5 text-[var(--text-muted)]">{agent}</td>
              {data[ai].map((count, hi) => (
                <td key={hi} className="p-0.5">
                  <div
                    className="mx-auto h-4 w-6 rounded-sm"
                    style={{ backgroundColor: cellColor(count) }}
                    title={`${agent} ${HOURS[hi]}h: ${count} lần từ chối`}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
