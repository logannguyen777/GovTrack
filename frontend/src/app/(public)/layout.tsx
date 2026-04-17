"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { User } from "lucide-react";
import { AIAssistantBubble } from "@/components/assistant/ai-assistant-bubble";
import { RoleSwitcher } from "@/components/layout/role-switcher";
import { ArchitectureLivePanel } from "@/components/public/architecture-live-panel";

// ---------------------------------------------------------------------------
// Senior mode — persisted in localStorage, applied as class on <body>
// ---------------------------------------------------------------------------

const SENIOR_KEY = "govflow-senior-mode";

function useSeniorMode() {
  const [active, setActive] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(SENIOR_KEY);
    const on = stored === "1";
    setActive(on);
    document.body.classList.toggle("senior-mode", on);
  }, []);

  function toggle() {
    setActive((prev) => {
      const next = !prev;
      localStorage.setItem(SENIOR_KEY, next ? "1" : "0");
      document.body.classList.toggle("senior-mode", next);
      return next;
    });
  }

  return { active, toggle };
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const senior = useSeniorMode();

  return (
    <div className="min-h-screen bg-[var(--bg-app)]" data-citizen="true">
      {/* Skip link — first focusable element */}
      <a href="#main" className="skip-link">
        Chuyển tới nội dung
      </a>

      <header className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link
            href="/portal"
            className="text-lg font-bold text-[var(--text-primary)]"
            aria-label="GovFlow — Trang chủ"
          >
            GovFlow
          </Link>

          <nav aria-label="Điều hướng chính" className="flex items-center gap-3">
            <Link
              href="/portal"
              className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              Trang chủ
            </Link>
            <Link
              href="/permission-demo"
              className="hidden text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] md:inline"
            >
              Permission Demo
            </Link>

            {/* Senior mode toggle */}
            <button
              type="button"
              onClick={senior.toggle}
              aria-pressed={senior.active}
              aria-label={
                senior.active
                  ? "Tắt chế độ người cao tuổi"
                  : "Bật chế độ người cao tuổi"
              }
              className={`hidden items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] sm:flex ${
                senior.active
                  ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                  : "border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)]"
              }`}
            >
              <User size={13} aria-hidden="true" />
              Chế độ người cao tuổi
            </button>

            <RoleSwitcher />
            <Link
              href="/auth/login"
              className="rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2"
            >
              Đăng nhập
            </Link>
          </nav>
        </div>
      </header>

      <div className="flex">
        <main
          id="main"
          role="main"
          aria-label="Nội dung chính"
          className="flex-1 min-w-0 lg:pr-[360px]"
        >
          {children}
        </main>
      </div>

      <ArchitectureLivePanel />
      <AIAssistantBubble />
    </div>
  );
}
