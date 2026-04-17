"use client";

/**
 * RoleSwitcher — persistent top-right dropdown that swaps persona via
 * real backend login (POST /api/auth/login). No mocking — each option
 * issues a fresh JWT so permission checks, clearance, and audit logs
 * reflect the chosen role.
 *
 * Use case: hackathon judges click once to see "the same case" from
 * citizen / intake / officer / leader / legal / security perspectives.
 */

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import { UserCog, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider";

interface Persona {
  username: string;
  label: string;
  role: string;
  clearance: number;
  landingPath: string;
  accent: string; // Tailwind text color
}

const PERSONAS: Persona[] = [
  // "Công dân" is unauthenticated — navigate directly without login
  { username: "",                 label: "Công dân (Portal)", role: "public_viewer",   clearance: 0, landingPath: "/portal",    accent: "text-slate-600 dark:text-slate-300" },
  { username: "staff_intake",     label: "Cán bộ tiếp nhận",  role: "staff_intake",    clearance: 0, landingPath: "/intake",    accent: "text-blue-600 dark:text-blue-300" },
  { username: "cv_qldt",          label: "Chuyên viên xử lý",  role: "staff_processor", clearance: 1, landingPath: "/inbox",     accent: "text-indigo-600 dark:text-indigo-300" },
  { username: "legal_expert",     label: "Pháp chế",           role: "legal",           clearance: 2, landingPath: "/consult",   accent: "text-purple-600 dark:text-purple-300" },
  { username: "ld_phong",         label: "Lãnh đạo",           role: "leader",          clearance: 2, landingPath: "/dashboard", accent: "text-amber-600 dark:text-amber-300" },
  { username: "security_officer", label: "An ninh",            role: "security",        clearance: 3, landingPath: "/security",  accent: "text-red-600 dark:text-red-300" },
  { username: "admin",            label: "Quản trị",           role: "admin",           clearance: 3, landingPath: "/dashboard", accent: "text-emerald-600 dark:text-emerald-300" },
];

export function RoleSwitcher() {
  const { user, login } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);
  const [switching, setSwitching] = React.useState<string | null>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);

  // Close on outside click / escape
  React.useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function swap(persona: Persona) {
    if (switching) return;
    setSwitching(persona.username || "citizen");
    try {
      // Empty username = citizen / public portal (no auth needed)
      if (!persona.username) {
        toast.success(`Đã chuyển sang: ${persona.label}`);
        setOpen(false);
        router.push(persona.landingPath);
        return;
      }
      await login(persona.username, "demo");
      toast.success(`Đã chuyển sang: ${persona.label}`);
      setOpen(false);
      if (pathname !== persona.landingPath) {
        router.push(persona.landingPath);
      } else {
        router.refresh();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "unknown error";
      toast.error(`Không đổi được vai trò: ${msg}`);
    } finally {
      setSwitching(null);
    }
  }

  const activePersona = PERSONAS.find((p) => p.username && p.username === user?.username);

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)]"
        aria-haspopup="menu"
        aria-expanded={open}
        title="Đổi vai trò (demo — giám khảo có thể thử mọi persona)"
      >
        <UserCog size={14} className="text-purple-600 dark:text-purple-400" />
        <span className="hidden sm:inline">
          {activePersona?.label ?? user?.username ?? "Chọn vai trò"}
        </span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1 w-72 overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-lg"
        >
          <div className="border-b border-[var(--border-subtle)] bg-gradient-to-r from-purple-50 to-violet-50 px-3 py-2 text-xs font-semibold text-purple-700 dark:from-purple-950 dark:to-violet-950 dark:text-purple-200">
            Role Switcher · demo mode
          </div>
          <div className="max-h-96 overflow-y-auto">
            {PERSONAS.map((p) => {
              const isActive = p.username !== "" && p.username === user?.username;
              const isPending = switching === (p.username || "citizen");
              return (
                <button
                  key={p.username || p.role}
                  type="button"
                  role="menuitem"
                  onClick={() => swap(p)}
                  disabled={Boolean(switching)}
                  className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs transition-colors hover:bg-[var(--bg-surface-raised)] ${
                    isActive ? "bg-[var(--bg-surface-raised)]" : ""
                  } disabled:cursor-not-allowed`}
                >
                  <div className="flex min-w-0 flex-col">
                    <span className={`font-medium ${p.accent}`}>{p.label}</span>
                    <span className="truncate font-mono text-[10px] text-[var(--text-muted)]">
                      {p.username} · clearance {p.clearance}
                    </span>
                  </div>
                  {isPending ? (
                    <Loader2 size={14} className="shrink-0 animate-spin text-[var(--text-muted)]" />
                  ) : isActive ? (
                    <Check size={14} className="shrink-0 text-[var(--accent-success)]" />
                  ) : null}
                </button>
              );
            })}
          </div>
          <div className="border-t border-[var(--border-subtle)] px-3 py-1.5 text-[10px] text-[var(--text-muted)]">
            Mỗi vai trò issue JWT riêng · password demo
          </div>
        </div>
      )}
    </div>
  );
}
