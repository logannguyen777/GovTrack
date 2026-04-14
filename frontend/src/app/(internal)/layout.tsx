"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { AppShell } from "@/components/layout/app-shell";

export default function InternalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/auth/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-app)]">
        <div className="animate-pulse text-[var(--text-muted)]">
          Đang tải...
        </div>
      </div>
    );
  }

  if (!user) return null;

  return <AppShell>{children}</AppShell>;
}
