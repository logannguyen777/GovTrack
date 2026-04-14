"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";

export default function RootPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (user) {
      router.replace("/dashboard");
    } else {
      router.replace("/portal");
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
      <div className="animate-pulse text-[var(--text-muted)]">Đang tải...</div>
    </div>
  );
}
