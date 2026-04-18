"use client";

/**
 * ArchitectureLivePanel — fixed right-rail panel visible on every public page.
 *
 * Purpose: live showcase of the Alibaba Cloud + Qwen3 stack for hackathon
 * judges. Subscribes to `public:system:activity` WS topic and renders events
 * as the system processes requests (LLM calls, vector search, GDB traversals,
 * OCR, OSS presigning, cache hits).
 *
 * Width: 360px on lg+, collapses to floating bottom-drawer button below lg.
 */

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Database,
  Network,
  ScanText,
  Cloud,
  Zap,
  Activity,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import {
  useActivityFeed,
  type ActivityEvent,
  type ActivityType,
} from "@/hooks/use-activity-feed";

// ---------------------------------------------------------------------------
// Event visual config (icon + color per type)
// ---------------------------------------------------------------------------

const TYPE_CONFIG: Record<
  ActivityType,
  { icon: React.ComponentType<{ size?: number; className?: string }>; color: string; bg: string }
> = {
  llm:    { icon: Sparkles, color: "text-purple-600 dark:text-purple-300", bg: "bg-purple-100 dark:bg-purple-950" },
  vector: { icon: Database, color: "text-blue-600 dark:text-blue-300",     bg: "bg-blue-100 dark:bg-blue-950" },
  graph:  { icon: Network,  color: "text-indigo-600 dark:text-indigo-300", bg: "bg-indigo-100 dark:bg-indigo-950" },
  ocr:    { icon: ScanText, color: "text-amber-600 dark:text-amber-300",   bg: "bg-amber-100 dark:bg-amber-950" },
  oss:    { icon: Cloud,    color: "text-sky-600 dark:text-sky-300",       bg: "bg-sky-100 dark:bg-sky-950" },
  cache:  { icon: Zap,      color: "text-emerald-600 dark:text-emerald-300", bg: "bg-emerald-100 dark:bg-emerald-950" },
};

// ---------------------------------------------------------------------------
// Stack rows (static — showcases the architecture)
// ---------------------------------------------------------------------------

interface StackRow {
  name: string;
  vendor: string;
  border: string;
}

const STACK: StackRow[] = [
  { name: "Qwen3-Max",          vendor: "Reasoning / tool-calling", border: "border-l-purple-500" },
  { name: "Qwen3-VL-Plus",      vendor: "OCR · multimodal",          border: "border-l-violet-500" },
  { name: "Qwen3-Embedding v3", vendor: "1024-dim vector search",    border: "border-l-indigo-500" },
  { name: "Alibaba GDB",        vendor: "Gremlin / TinkerPop",       border: "border-l-blue-500" },
  { name: "Hologres + pgvector", vendor: "Analytics + Proxima",       border: "border-l-sky-500" },
  { name: "Alibaba Cloud OSS",  vendor: "S3-compat blob storage",    border: "border-l-amber-500" },
  { name: "Model Studio",       vendor: "DashScope API gateway",     border: "border-l-emerald-500" },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function formatRelative(timestamp: string): string {
  const age = Date.now() - new Date(timestamp).getTime();
  if (age < 2000) return "vừa xong";
  if (age < 60_000) return `${Math.floor(age / 1000)}s`;
  if (age < 3_600_000) return `${Math.floor(age / 60_000)}m`;
  return `${Math.floor(age / 3_600_000)}h`;
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const { icon: Icon, color, bg } = TYPE_CONFIG[event.type];
  const [, force] = React.useReducer((x: number) => x + 1, 0);
  // Re-render every 5s so "vừa xong / 5s / 10s" stays fresh
  React.useEffect(() => {
    const id = setInterval(force, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
      className="flex items-start gap-2 border-b border-[var(--border-subtle)] px-3 py-2 last:border-b-0"
    >
      <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${bg}`}>
        <Icon size={14} className={color} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-[var(--text-primary)]">
          {event.label}
        </p>
        {event.detail && (
          <p className="truncate font-mono text-[10px] text-[var(--text-muted)]">
            {event.detail}
            {event.duration_ms ? ` · ${Math.round(event.duration_ms)}ms` : ""}
          </p>
        )}
      </div>
      <span className="shrink-0 self-start text-[10px] text-[var(--text-muted)]">
        {formatRelative(event.timestamp)}
      </span>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

function PanelBody() {
  const events = useActivityFeed();

  return (
    <div className="flex h-full flex-col bg-[var(--bg-surface)]">
      {/* Brand strip */}
      <div className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-violet-600 px-4 py-3 text-white">
        <Sparkles size={16} className="shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider opacity-80">
            Live Architecture
          </p>
          <p className="text-sm font-bold">GovFlow × Alibaba Cloud × Qwen3</p>
        </div>
      </div>

      {/* Stack card */}
      <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] p-3">
        <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          <Activity size={11} />
          Stack
        </p>
        <div className="grid grid-cols-1 gap-1.5">
          {STACK.map((s) => (
            <div
              key={s.name}
              className={`flex items-center justify-between border-l-2 ${s.border} bg-[var(--bg-surface)] px-2 py-1`}
            >
              <div className="min-w-0">
                <p className="truncate text-[11px] font-semibold text-[var(--text-primary)]">
                  {s.name}
                </p>
                <p className="truncate text-[9px] text-[var(--text-muted)]">
                  {s.vendor}
                </p>
              </div>
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]" />
            </div>
          ))}
        </div>
      </div>

      {/* Live feed */}
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2">
          <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            Live activity
          </p>
          <span className="font-mono text-[10px] text-[var(--text-muted)]">
            {events.length} sự kiện
          </span>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {events.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
              <Activity size={24} className="text-[var(--text-muted)]" />
              <p className="text-xs text-[var(--text-muted)]">
                Đang chờ hệ thống hoạt động.
                <br />
                Tương tác với cổng để thấy các agent làm việc.
              </p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {events.map((e) => (
                <ActivityRow key={e.id} event={e} />
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-[var(--border-subtle)] px-3 py-2 text-[10px] text-[var(--text-muted)]">
        Dữ liệu trực tiếp từ Agent Runtime · Không chứa PII
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Responsive wrapper
// ---------------------------------------------------------------------------

export function ArchitectureLivePanel() {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [desktopOpen, setDesktopOpen] = React.useState(true);

  return (
    <>
      {/* Desktop: fixed right rail, always open by default */}
      <aside
        className={`fixed right-0 top-14 bottom-0 z-20 hidden w-[360px] border-l border-[var(--border-subtle)] shadow-lg transition-transform duration-300 lg:block ${
          desktopOpen ? "translate-x-0" : "translate-x-[320px]"
        }`}
        aria-label="Architecture Live Panel"
      >
        <button
          type="button"
          onClick={() => setDesktopOpen((v) => !v)}
          className="absolute left-0 top-1/2 -translate-x-full rounded-l-lg border border-r-0 border-[var(--border-subtle)] bg-[var(--bg-surface)] px-1 py-3 text-[var(--text-muted)] shadow-md hover:text-[var(--text-primary)]"
          aria-label={desktopOpen ? "Thu gọn panel" : "Mở panel"}
        >
          {desktopOpen ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
        <PanelBody />
      </aside>

      {/* Mobile: floating FAB */}
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="fixed bottom-24 right-4 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-violet-700 text-white shadow-lg lg:hidden"
        aria-label="Xem Architecture Live Panel"
      >
        <Activity size={18} />
      </button>

      {/* Mobile: bottom drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-50 bg-black/40 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              className="fixed inset-x-0 bottom-0 z-50 h-[70vh] overflow-hidden rounded-t-2xl border-t border-[var(--border-subtle)] shadow-2xl lg:hidden"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
            >
              <PanelBody />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
