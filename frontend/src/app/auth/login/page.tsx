"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { Suspense } from "react";

const DEMO_USERS = [
  {
    username: "admin",
    label: "Quản trị viên hệ thống",
    desc: "Toàn quyền quản lý hệ thống, xem audit, quản lý phân quyền",
    role: "admin",
    clearance: 4,
  },
  {
    username: "ld_phong",
    label: "Trần Thị Lãnh Đạo",
    desc: "Lãnh đạo phòng — phê duyệt hồ sơ, xem bảng điều hành",
    role: "leader",
    clearance: 3,
  },
  {
    username: "cv_qldt",
    label: "Nguyễn Văn Chuyên Viên",
    desc: "Chuyên viên quản lý đô thị — xử lý hồ sơ xây dựng, đất đai",
    role: "officer",
    clearance: 2,
  },
  {
    username: "staff_intake",
    label: "Lê Văn Tiếp Nhận",
    desc: "Cán bộ tiếp nhận — nhận và phân loại hồ sơ mới",
    role: "officer",
    clearance: 1,
  },
  {
    username: "legal_expert",
    label: "Phạm Thị Pháp Lý",
    desc: "Chuyên viên pháp lý — kiểm tra tuân thủ, tra cứu luật",
    role: "officer",
    clearance: 3,
  },
  {
    username: "security_officer",
    label: "Hoàng Văn Bảo Mật",
    desc: "Cán bộ bảo mật — quản lý phân loại tài liệu, audit",
    role: "admin",
    clearance: 4,
  },
];

const ROLE_LABELS: Record<string, string> = {
  admin: "Quản trị",
  leader: "Lãnh đạo",
  officer: "Chuyên viên",
};

const CLEARANCE_LABELS = ["Không mật", "Mật", "Tối mật", "Tuyệt mật", "Đặc biệt"];

function LoginContent() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<string | null>(null);

  async function handleLogin(username: string) {
    setError("");
    setLoading(username);
    try {
      await login(username, "demo");
      router.push(params.get("redirect") || "/dashboard");
    } catch {
      setError("Đăng nhập thất bại. Kiểm tra backend đang chạy.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
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

        <div className="space-y-2">
          {DEMO_USERS.map((u) => (
            <button
              key={u.username}
              onClick={() => handleLogin(u.username)}
              disabled={loading !== null}
              className="flex w-full items-center justify-between rounded-md border border-[var(--border-subtle)] px-4 py-3 text-left text-sm transition-colors hover:bg-[var(--bg-surface-raised)] disabled:opacity-50"
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
                <div className="ml-2 h-4 w-4 animate-spin rounded-full border-2 border-[var(--accent-primary)] border-t-transparent" />
              )}
            </button>
          ))}
        </div>

        {error && (
          <p className="text-sm text-[var(--accent-error)]">{error}</p>
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
