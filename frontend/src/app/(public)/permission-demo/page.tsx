"use client";

/**
 * Permission Demo Scene — 3 tiers side-by-side for hackathon judges.
 *
 * Tier 1 SDK Guard (compile-time allowlist)
 * Tier 2 GDB RBAC (runtime INSERT/UPDATE privileges per agent)
 * Tier 3 Property Mask (clearance-aware field dissolve)
 *
 * Unlike /security which is auth-gated, this page is public — judges coming
 * in via portal can see the permission engine without logging in.
 */

import * as React from "react";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  ShieldAlert,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
  Lock,
} from "lucide-react";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SceneAResponse {
  status: "DENIED" | "OK";
  tier: string;
  agent?: string;
  violation?: string;
  detail?: string;
}

interface SceneCResponse {
  status: "OK";
  tier: "PROPERTY_MASK";
  before_elevation: Record<string, unknown>;
  after_elevation: Record<string, unknown>;
  dissolved_fields: string[];
}

// ---------------------------------------------------------------------------
// Scene A + B shared card (deny scenarios)
// ---------------------------------------------------------------------------

function DenyScene({
  title,
  tier,
  description,
  endpoint,
  sceneLetter,
}: {
  title: string;
  tier: string;
  description: string;
  endpoint: string;
  sceneLetter: "A" | "B";
}) {
  const [state, setState] = React.useState<
    "idle" | "loading" | "denied" | "error"
  >("idle");
  const [response, setResponse] = React.useState<SceneAResponse | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  async function trigger() {
    setState("loading");
    try {
      const r = await fetch(endpoint, { method: "POST" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = (await r.json()) as SceneAResponse;
      setResponse(data);
      setState("denied");
      toast.success(`Scene ${sceneLetter}: ${data.tier} denied request`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "unknown");
      setState("error");
    }
  }

  return (
    <div className="flex flex-col rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-950">
          <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-300" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-red-600 dark:text-red-300">
            Scene {sceneLetter} · {tier}
          </p>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--text-primary)]">
            {title}
          </h3>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            {description}
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={trigger}
        disabled={state === "loading"}
        className="mt-4 flex items-center justify-center gap-2 rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {state === "loading" ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <ShieldAlert size={14} />
        )}
        {state === "loading" ? "Đang kiểm tra..." : "Thử attack"}
      </button>

      {state === "denied" && response && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 font-mono text-[11px] leading-relaxed dark:border-red-800 dark:bg-red-950"
        >
          <div className="flex items-center gap-1.5 font-sans">
            <XCircle className="h-4 w-4 text-red-600 dark:text-red-300" />
            <span className="font-bold text-red-700 dark:text-red-200">
              DENIED
            </span>
          </div>
          <pre className="mt-2 whitespace-pre-wrap text-red-900 dark:text-red-200">
            {JSON.stringify(response, null, 2)}
          </pre>
        </motion.div>
      )}

      {state === "error" && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          Lỗi: {err}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scene C — side-by-side before/after elevation
// ---------------------------------------------------------------------------

function SceneC() {
  const [state, setState] = React.useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [data, setData] = React.useState<SceneCResponse | null>(null);
  const [elevated, setElevated] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  async function trigger() {
    setState("loading");
    try {
      const r = await fetch("/api/demo/permissions/scene-c/clearance-elevation", {
        method: "POST",
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = (await r.json()) as SceneCResponse;
      setData(d);
      setState("done");
      setElevated(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "unknown");
      setState("error");
    }
  }

  const displayed = elevated
    ? data?.after_elevation
    : data?.before_elevation;

  return (
    <div className="flex flex-col rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 lg:col-span-2">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950">
          <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-300" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-300">
            Scene C · PROPERTY_MASK
          </p>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--text-primary)]">
            Clearance Elevation — property mask tan biến
          </h3>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            User UNCLASSIFIED chỉ thấy field được mask. Sau khi elevate lên
            CONFIDENTIAL, mask dissolve và giá trị thật lộ ra.
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={trigger}
        disabled={state === "loading"}
        className="mt-4 flex w-fit items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {state === "loading" ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />}
        {state === "idle" ? "Bắt đầu demo" : state === "loading" ? "..." : "Chạy lại"}
      </button>

      {state === "done" && data && (
        <>
          {/* Toggle */}
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] p-3">
            <button
              type="button"
              onClick={() => setElevated((v) => !v)}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                elevated
                  ? "bg-emerald-600 text-white"
                  : "border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)]"
              }`}
            >
              {elevated ? <Eye size={12} /> : <EyeOff size={12} />}
              {elevated ? "CONFIDENTIAL" : "UNCLASSIFIED"}
            </button>
            <span className="text-xs text-[var(--text-muted)]">
              Click để elevate / demote clearance
            </span>
            {data.dissolved_fields.length > 0 && (
              <span className="ml-auto rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-200">
                {data.dissolved_fields.length} field tan biến
              </span>
            )}
          </div>

          {/* Record display */}
          <div className="mt-3 overflow-hidden rounded-lg border border-[var(--border-subtle)]">
            {Object.entries(displayed ?? {}).map(([k, v]) => {
              const isDissolved = data.dissolved_fields.includes(k);
              return (
                <div
                  key={k}
                  className={`flex items-center gap-3 border-b border-[var(--border-subtle)] px-3 py-2 last:border-b-0 ${
                    isDissolved
                      ? elevated
                        ? "bg-emerald-50 dark:bg-emerald-950/50"
                        : "bg-red-50 dark:bg-red-950/50"
                      : ""
                  }`}
                >
                  <span className="w-36 shrink-0 font-mono text-[11px] text-[var(--text-muted)]">
                    {k}
                  </span>
                  <motion.span
                    key={String(v)}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={`flex-1 truncate text-xs ${
                      String(v).startsWith("[CLASSIFIED") || String(v).startsWith("[REDACTED")
                        ? "font-mono text-red-600 dark:text-red-300"
                        : "text-[var(--text-primary)]"
                    }`}
                  >
                    {String(v)}
                  </motion.span>
                  {isDissolved && (
                    <Lock
                      size={12}
                      className={
                        elevated
                          ? "text-emerald-500"
                          : "text-red-500"
                      }
                    />
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      {state === "error" && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          Lỗi: {err}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function PermissionDemoPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-violet-700 text-white shadow-lg">
          <ShieldCheck size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Permission Engine — 3 tầng bảo vệ
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Đây là yếu tố phân biệt GovFlow với cổng DVC quốc gia. Từng tầng
            từ chối request trái phép và tạo audit log.
          </p>
        </div>
      </div>

      {/* Tier overview */}
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          {
            icon: ShieldAlert,
            title: "Tier 1 — SDK Guard",
            description: "Allowlist compile-time trên mỗi agent profile. Chặn truy vấn tới property bị cấm trước khi chạm DB.",
            color: "text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-950",
          },
          {
            icon: Lock,
            title: "Tier 2 — GDB RBAC",
            description: "Privileges INSERT / UPDATE / DELETE per vertex label. Runtime check trong GDB.",
            color: "text-amber-600 dark:text-amber-300 bg-amber-50 dark:bg-amber-950",
          },
          {
            icon: ShieldCheck,
            title: "Tier 3 — Property Mask",
            description: "Field-level mask theo clearance (0-3). Nâng quyền → mask tan biến.",
            color: "text-emerald-600 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950",
          },
        ].map((t) => {
          const Icon = t.icon;
          return (
            <div
              key={t.title}
              className="flex flex-col gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"
            >
              <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${t.color}`}>
                <Icon size={18} />
              </div>
              <p className="text-sm font-semibold text-[var(--text-primary)]">
                {t.title}
              </p>
              <p className="text-xs text-[var(--text-muted)]">{t.description}</p>
            </div>
          );
        })}
      </div>

      {/* Scenes */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <DenyScene
          sceneLetter="A"
          tier="SDK_GUARD"
          title="SDK Guard từ chối truy cập national_id"
          description="Summarizer agent cố đọc property national_id — bị chặn trước khi chạm GDB."
          endpoint="/api/demo/permissions/scene-a/sdk-guard-rejection"
        />
        <DenyScene
          sceneLetter="B"
          tier="GDB_RBAC"
          title="GDB RBAC từ chối CREATE Gap vertex"
          description="LegalSearch agent cố addV('Gap') — không có INSERT privilege trên Gap."
          endpoint="/api/demo/permissions/scene-b/rbac-rejection"
        />
        <SceneC />
      </div>

      <div className="mt-6 flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] p-3 text-xs text-[var(--text-muted)]">
        <CheckCircle2 size={14} className="text-emerald-500" />
        Mọi denial được ghi vào <code className="font-mono">audit_events_flat</code> (Hologres) + AuditEvent vertex (GDB) — truy vết được cho kiểm tra.
      </div>
    </div>
  );
}
