"use client";

import { useCallback, useState } from "react";
import { useWSTopic, useWSConnection } from "@/hooks/use-ws";
import { useAuditEvents } from "@/hooks/use-audit";
import { RedactedField } from "@/components/ui/redacted-field";
import { apiClient } from "@/lib/api";
import type { WSMessage, AuditEventResponse } from "@/lib/types";
import { toast } from "sonner";
import { Shield, AlertTriangle, Eye } from "lucide-react";

export default function SecurityConsole() {
  const [liveEvents, setLiveEvents] = useState<AuditEventResponse[]>([]);
  const [elevationActive, setElevationActive] = useState(false);
  const [triggeringScene, setTriggeringScene] = useState<string | null>(null);
  const { data: historicalEvents, error: auditError, refetch: refetchAudit } = useAuditEvents({ limit: 50 });

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
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-[var(--accent-primary)]" />
        <h1 className="text-2xl font-bold">Trung tâm bảo mật</h1>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Live audit log */}
        <div className="col-span-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Nhật ký kiểm tra (Live)</h3>
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
              {allEvents.length === 0 && (
                <p className="text-[var(--text-muted)]">
                  Chưa có sự kiện. Kết nối WebSocket để nhận cập nhật realtime.
                </p>
              )}
              {allEvents.map((event, i) => {
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
        <div className="space-y-4">
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
