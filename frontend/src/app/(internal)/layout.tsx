"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider";
import { AppShell } from "@/components/layout/app-shell";
import { useWSConnection } from "@/hooks/use-ws";
import { ArchitectureLivePanel } from "@/components/public/architecture-live-panel";
import { AIAssistantBubble } from "@/components/assistant/ai-assistant-bubble";
import { canAccessRoute, landingForRole, ROLE_LABELS } from "@/lib/roles";
import { WSCacheInvalidator } from "@/components/providers/ws-cache-invalidator";

// ---------------------------------------------------------------------------
// JWT expiry helper (client-side only — no secret verification)
// ---------------------------------------------------------------------------

function isTokenExpired(token: string): boolean {
  try {
    const payloadB64 = token.split(".")[1];
    if (!payloadB64) return true;
    const json = atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as Record<string, unknown>;
    const exp = payload.exp;
    if (typeof exp !== "number") return false; // no exp claim → treat as valid
    return exp * 1000 < Date.now();
  } catch {
    return true; // malformed token → treat as expired
  }
}

export default function InternalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, token, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useWSConnection();

  // Auth + route-access check
  useEffect(() => {
    if (isLoading) return;

    // No user at all → redirect to login
    if (!user) {
      router.replace(`/auth/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    // Client-side JWT expiry check
    if (token && isTokenExpired(token)) {
      router.replace(`/auth/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    // Role-based route access check
    if (!canAccessRoute(user.role, pathname)) {
      const landing = landingForRole(user.role);
      toast.info(
        `Vai trò ${ROLE_LABELS[user.role] ?? user.role} không truy cập được trang này — đã chuyển đến ${landing}`,
      );
      router.replace(landing);
    }
  }, [user, token, isLoading, pathname, router]);

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

  return (
    <>
      {/* Skip-link — first focusable element, revealed on keyboard focus */}
      <a href="#main-content" className="skip-link">
        Chuyển tới nội dung
      </a>
      <WSCacheInvalidator />
      <AppShell>{children}</AppShell>
      <ArchitectureLivePanel />
      <AIAssistantBubble />
    </>
  );
}
