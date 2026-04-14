import Link from "next/link";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[var(--bg-app)]">
      <header className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/portal" className="text-lg font-bold text-[var(--text-primary)]">
            GovFlow
          </Link>
          <nav className="flex items-center gap-4">
            <Link
              href="/portal"
              className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              Trang chủ
            </Link>
            <Link
              href="/auth/login"
              className="rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white"
            >
              Đăng nhập
            </Link>
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
