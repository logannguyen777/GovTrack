"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { ROLE_LABELS, landingForRole } from "@/lib/roles";

const DEMO_USERS = [
  {
    username: "admin",
    label: "Quản trị viên hệ thống",
    desc: "Toàn quyền quản lý hệ thống, xem audit, quản lý phân quyền",
    role: "admin",
    clearance: 3,
  },
  {
    username: "ld_phong",
    label: "Trần Thị Lãnh Đạo",
    desc: "Lãnh đạo phòng — phê duyệt hồ sơ, xem bảng điều hành",
    role: "leader",
    clearance: 2,
  },
  {
    username: "cv_qldt",
    label: "Nguyễn Văn Chuyên Viên",
    desc: "Chuyên viên quản lý đô thị — xử lý hồ sơ xây dựng, đất đai",
    role: "staff_processor",
    clearance: 1,
  },
  {
    username: "staff_intake",
    label: "Lê Văn Tiếp Nhận",
    desc: "Cán bộ tiếp nhận — nhận và phân loại hồ sơ mới",
    role: "staff_intake",
    clearance: 0,
  },
  {
    username: "legal_expert",
    label: "Phạm Thị Pháp Lý",
    desc: "Chuyên viên pháp lý — kiểm tra tuân thủ, tra cứu luật",
    role: "legal",
    clearance: 2,
  },
  {
    username: "security_officer",
    label: "Hoàng Văn Bảo Mật",
    desc: "Cán bộ bảo mật — quản lý phân loại tài liệu, audit",
    role: "security",
    clearance: 3,
  },
];

const CLEARANCE_LABELS = ["Thông thường", "Mật", "Tối mật", "Tuyệt mật"];

/**
 * Validates a ?next= redirect target.
 * Must start with "/" and must NOT contain "://" or start with "//".
 */
function isSafeNext(next: string | null): next is string {
  if (!next) return false;
  if (!next.startsWith("/")) return false;
  if (next.startsWith("//")) return false;
  if (next.includes("://")) return false;
  return true;
}

function LoginContent() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualUsername, setManualUsername] = useState("");
  const [manualPassword, setManualPassword] = useState("");

  async function handleLogin(username: string, password = "demo") {
    setError("");
    setLoading(username);
    try {
      const result = await login(username, password);
      // Prefer ?next= (set by middleware/401 handler) over legacy ?redirect=
      const next = params.get("next") ?? params.get("redirect");
      const destination = isSafeNext(next) ? next : landingForRole(result?.role);
      router.push(destination);
    } catch {
      setError("Đăng nhập thất bại. Kiểm tra backend đang chạy.");
    } finally {
      setLoading(null);
    }
  }

  async function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!manualUsername.trim()) return;
    await handleLogin(manualUsername.trim(), manualPassword);
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--bg-app)] p-4">
      <div className="w-full max-w-md">
        <Link
          href="/portal"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] rounded"
        >
          <ArrowLeft className="h-4 w-4" />
          Về trang chủ
        </Link>
      </div>
      <div className="w-full max-w-md space-y-6 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-lg">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            GovFlow
          </h1>
          <p className="mt-0.5 text-xs text-[var(--text-muted)]">
            Hệ thống xử lý thủ tục hành chính thông minh
          </p>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Chọn tài khoản để đăng nhập vào hệ thống demo
          </p>
        </div>

        <div className="space-y-2" role="list" aria-label="Tài khoản demo">
          {DEMO_USERS.map((u) => (
            <button
              key={u.username}
              onClick={() => handleLogin(u.username)}
              disabled={loading !== null}
              role="listitem"
              aria-label={`Đăng nhập với tài khoản ${u.label}, vai trò ${ROLE_LABELS[u.role] ?? u.role}`}
              className="flex w-full items-center justify-between rounded-md border border-[var(--border-subtle)] px-4 py-3 text-left text-sm transition-colors hover:bg-[var(--bg-surface-raised)] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            >
              <div className="min-w-0 flex-1">
                <p className="font-medium text-[var(--text-primary)]">
                  {u.label}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  {u.desc}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-[var(--bg-surface-raised)] px-2 py-0.5 text-[10px] font-medium">
                  {ROLE_LABELS[u.role] ?? u.role}
                </span>
                <span className="text-[10px] text-[var(--text-muted)]">
                  L{u.clearance}: {CLEARANCE_LABELS[u.clearance]}
                </span>
              </div>
              {loading === u.username && (
                <div
                  className="ml-2 h-4 w-4 animate-spin rounded-full border-2 border-t-transparent"
                  style={{ borderColor: "var(--accent-primary)", borderTopColor: "transparent" }}
                  aria-label="Đang đăng nhập..."
                />
              )}
            </button>
          ))}
        </div>

        {/* Manual login collapsible */}
        <div className="border-t border-[var(--border-subtle)] pt-4">
          <button
            type="button"
            onClick={() => setManualOpen((v) => !v)}
            className="flex w-full items-center justify-between text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] rounded"
            aria-expanded={manualOpen}
            aria-controls="manual-login-form"
          >
            <span>Đăng nhập bằng tài khoản khác</span>
            {manualOpen ? (
              <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </button>

          {manualOpen && (
            <form
              id="manual-login-form"
              onSubmit={handleManualSubmit}
              className="mt-3 space-y-3"
              aria-label="Đăng nhập bằng tài khoản tùy chỉnh"
            >
              <div>
                <label
                  htmlFor="manual-username"
                  className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
                >
                  Tên đăng nhập
                </label>
                <input
                  id="manual-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  value={manualUsername}
                  onChange={(e) => setManualUsername(e.target.value)}
                  disabled={loading !== null}
                  placeholder="Tên đăng nhập"
                  className="w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
                />
              </div>
              <div>
                <label
                  htmlFor="manual-password"
                  className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
                >
                  Mật khẩu
                </label>
                <input
                  id="manual-password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  value={manualPassword}
                  onChange={(e) => setManualPassword(e.target.value)}
                  disabled={loading !== null}
                  placeholder="Mật khẩu"
                  className="w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
                />
              </div>
              <button
                type="submit"
                disabled={loading !== null || !manualUsername.trim()}
                className="flex w-full items-center justify-center rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              >
                {loading === manualUsername ? (
                  <div
                    className="h-4 w-4 animate-spin rounded-full border-2 border-t-transparent"
                    style={{ borderColor: "white", borderTopColor: "transparent" }}
                    aria-label="Đang đăng nhập..."
                  />
                ) : (
                  "Đăng nhập"
                )}
              </button>
            </form>
          )}
        </div>

        {error && (
          <p className="text-sm" style={{ color: "var(--accent-error)" }} role="alert">
            {error}
          </p>
        )}

        <p className="text-center text-xs text-[var(--text-muted)]">
          Mật khẩu mặc định: demo
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
          <div className="animate-pulse text-[var(--text-muted)]">
            Đang tải...
          </div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
