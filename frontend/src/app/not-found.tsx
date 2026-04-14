import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
      <div className="text-center">
        <FileQuestion className="mx-auto h-16 w-16 text-[var(--text-muted)]" />
        <h1 className="mt-4 text-4xl font-bold text-[var(--text-primary)]">
          404
        </h1>
        <p className="mt-2 text-lg text-[var(--text-secondary)]">
          Trang không tồn tại
        </p>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Trang bạn đang tìm kiếm không có hoặc đã được di chuyển.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            href="/portal"
            className="rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Về trang chủ
          </Link>
          <Link
            href="/auth/login"
            className="rounded-md border border-[var(--border-default)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-surface-raised)]"
          >
            Đăng nhập
          </Link>
        </div>
      </div>
    </div>
  );
}
