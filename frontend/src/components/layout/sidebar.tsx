"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  Inbox,
  ShieldCheck,
  MessagesSquare,
  FileText,
  GitBranch,
  Lock,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { motion } from "framer-motion";
import { useAuth } from "@/components/providers/auth-provider";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useWSState } from "@/hooks/use-ws";
import { ROLE_LABELS } from "@/lib/roles";

// ---------------------------------------------------------------------------
// Nav item definitions
// ---------------------------------------------------------------------------

// Each nav item lists roles allowed to see it. Matches backend permission
// checks: /leadership/* is leader/admin only; /security is admin only.
interface NavItemSpec {
  label: string;
  href: string;
  icon: React.ElementType;
  roles?: string[]; // undefined = visible to all authenticated users
}

const NAV_ITEMS: NavItemSpec[] = [
  { label: "Bảng điều hành", href: "/dashboard",  icon: LayoutDashboard, roles: ["admin", "leader", "security"] },
  { label: "Tiếp nhận",       href: "/intake",     icon: Upload,        roles: ["admin", "leader", "staff_intake", "staff_processor", "security"] },
  { label: "Hồ sơ đến",       href: "/inbox",      icon: Inbox,         roles: ["admin", "leader", "staff_intake", "staff_processor", "legal", "security"] },
  { label: "Tuân thủ",         href: "/compliance", icon: ShieldCheck,   roles: ["admin", "leader", "staff_processor", "legal", "security"] },
  { label: "Xin ý kiến",      href: "/consult",    icon: MessagesSquare,roles: ["admin", "leader", "staff_processor", "legal", "security"] },
  { label: "Tài liệu",        href: "/documents",  icon: FileText,      roles: ["admin", "leader", "staff_intake", "staff_processor", "legal", "security"] },
  { label: "Theo dõi AI",      href: "/trace",      icon: GitBranch,     roles: ["admin", "leader", "staff_processor", "legal", "security"] },
  { label: "Bảo mật",         href: "/security",   icon: Lock,          roles: ["admin", "security"] },
];

// ---------------------------------------------------------------------------
// Clearance level badge config
// ---------------------------------------------------------------------------

const CLEARANCE_LABELS: Record<number, { label: string; className: string }> = {
  0: { label: "Thông thường", className: "bg-[var(--classification-unclassified)] text-white" },
  1: { label: "Mật",          className: "bg-[var(--classification-confidential)] text-black" },
  2: { label: "Tối mật",      className: "bg-[var(--classification-secret)] text-white" },
  3: { label: "Tuyệt mật",    className: "bg-[var(--classification-top-secret)] text-white" },
};

// ---------------------------------------------------------------------------
// Shared link className builder
// ---------------------------------------------------------------------------

function navLinkClass(isActive: boolean) {
  return cn(
    "group relative flex h-10 items-center gap-3 rounded-[var(--radius-md)] px-3",
    "outline-none transition-colors duration-[var(--duration-micro)]",
    "focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
    "hover:bg-[var(--bg-surface-raised)]",
    isActive
      ? "bg-[var(--bg-surface-raised)] text-[var(--text-primary)]"
      : "text-[var(--text-secondary)]",
  );
}

// ---------------------------------------------------------------------------
// NavItem — collapsed shows tooltip, expanded shows icon + label
// ---------------------------------------------------------------------------

interface NavItemProps {
  href: string;
  label: string;
  icon: React.ElementType;
  isActive: boolean;
  collapsed: boolean;
}

function NavItem({ href, label, icon: Icon, isActive, collapsed }: NavItemProps) {
  const iconEl = (
    <Icon
      size={18}
      aria-hidden="true"
      className={cn(
        "shrink-0 transition-colors duration-[var(--duration-micro)]",
        isActive ? "text-[var(--accent-primary)]" : "text-[var(--text-muted)]",
        "group-hover:text-[var(--text-primary)]",
      )}
    />
  );

  if (collapsed) {
    // When collapsed, render TooltipTrigger with render prop so the <Link>
    // itself is the trigger element (base-ui render prop pattern).
    return (
      <Tooltip>
        <TooltipTrigger
          render={
            <Link
              href={href}
              aria-label={label}
              aria-current={isActive ? "page" : undefined}
              className={navLinkClass(isActive)}
            >
              {isActive && (
                <span
                  aria-hidden="true"
                  className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-[var(--accent-primary)]"
                />
              )}
              {iconEl}
            </Link>
          }
        />
        <TooltipContent side="right" sideOffset={8}>
          {label}
        </TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Link
      href={href}
      aria-label={label}
      aria-current={isActive ? "page" : undefined}
      className={navLinkClass(isActive)}
    >
      {isActive && (
        <span
          aria-hidden="true"
          className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-[var(--accent-primary)]"
        />
      )}
      {iconEl}
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.15, ease: [0.25, 1, 0.5, 1] }}
        className="truncate text-sm font-medium leading-none"
      >
        {label}
      </motion.span>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const WS_INDICATOR = {
  connected: { color: "bg-green-500", label: "Kết nối" },
  connecting: { color: "bg-amber-500 animate-pulse", label: "Đang kết nối..." },
  disconnected: { color: "bg-red-500", label: "Mất kết nối" },
} as const;

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const wsState = useWSState();

  const clearanceInfo = user
    ? (CLEARANCE_LABELS[user.clearance_level] ?? CLEARANCE_LABELS[0])
    : CLEARANCE_LABELS[0];

  return (
    <TooltipProvider delay={300}>
      <motion.aside
        aria-label="Thanh điều hướng chính"
        initial={false}
        animate={{ width: collapsed ? 64 : 240 }}
        transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
        style={{
          backgroundColor: "var(--bg-surface)",
          borderRight: "1px solid var(--border-subtle)",
        }}
        className="flex h-screen shrink-0 flex-col overflow-hidden"
      >
        {/* ---------------------------------------------------------------- */}
        {/* Logo                                                              */}
        {/* ---------------------------------------------------------------- */}
        <div
          className="flex h-14 items-center gap-2.5 border-b px-4 shrink-0"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            aria-hidden="true"
            className="shrink-0"
          >
            <path
              d="M14 2L4 6v8c0 5.5 4.3 10.7 10 12 5.7-1.3 10-6.5 10-12V6L14 2z"
              fill="var(--accent-primary)"
              opacity="0.9"
            />
            <path
              d="M10 14l2.5 2.5L18 11"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.15, ease: [0.25, 1, 0.5, 1] }}
              className="flex flex-col leading-tight"
            >
              <span
                className="text-sm font-bold tracking-tight"
                style={{ color: "var(--text-primary)" }}
              >
                GovFlow
              </span>
              <span
                className="text-[10px] font-medium uppercase tracking-widest"
                style={{ color: "var(--text-muted)" }}
              >
                Hệ thống TTHC
              </span>
            </motion.div>
          )}
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Nav items                                                         */}
        {/* ---------------------------------------------------------------- */}
        <nav
          aria-label="Điều hướng"
          className="flex flex-1 flex-col gap-0.5 overflow-y-auto overflow-x-hidden p-2"
        >
          {NAV_ITEMS.filter(
            (item) => !item.roles || (user && item.roles.includes(user.role)),
          ).map(({ label, href, icon }) => {
            const isActive =
              pathname === href || pathname.startsWith(href + "/");
            return (
              <NavItem
                key={href}
                href={href}
                label={label}
                icon={icon}
                isActive={isActive}
                collapsed={collapsed}
              />
            );
          })}
        </nav>

        {/* ---------------------------------------------------------------- */}
        {/* WS Status + Qwen branding                                         */}
        {/* ---------------------------------------------------------------- */}
        <div className="shrink-0 px-3 py-1.5">
          <div className="flex items-center gap-2">
            <span
              className={cn("inline-block h-2 w-2 rounded-full", WS_INDICATOR[wsState].color)}
              aria-label={WS_INDICATOR[wsState].label}
            />
            {!collapsed && (
              <span className="text-[10px] text-[var(--text-muted)]">
                {WS_INDICATOR[wsState].label}
              </span>
            )}
          </div>
          {!collapsed && (
            <p className="mt-1 text-[9px] text-[var(--text-muted)]">
              Powered by Qwen3
            </p>
          )}
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* User info                                                         */}
        {/* ---------------------------------------------------------------- */}
        {user && (
          <div
            className="shrink-0 border-t px-2 py-3"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <div
              className={cn(
                "flex items-center gap-2.5 rounded-[var(--radius-md)] px-2 py-2",
                "bg-[var(--bg-surface-raised)]",
              )}
            >
              {/* Initials avatar */}
              <div
                aria-hidden="true"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold uppercase text-white"
                style={{ backgroundColor: "var(--accent-primary)" }}
              >
                {(user.full_name ?? user.username).slice(0, 2)}
              </div>

              {!collapsed && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.15, ease: [0.25, 1, 0.5, 1] }}
                  className="flex min-w-0 flex-col gap-0.5"
                >
                  <span
                    className="truncate text-xs font-semibold leading-none"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {user.full_name || user.username}
                  </span>
                  <span
                    className={cn(
                      "inline-flex w-fit items-center rounded-sm px-1.5 py-0.5",
                      "text-[9px] font-bold uppercase tracking-widest",
                      clearanceInfo.className,
                    )}
                  >
                    {ROLE_LABELS[user.role] ?? user.role}
                  </span>
                </motion.div>
              )}
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Collapse toggle                                                   */}
        {/* ---------------------------------------------------------------- */}
        <div
          className="shrink-0 border-t p-2"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          {collapsed ? (
            <Tooltip>
              <TooltipTrigger
                render={
                  <button
                    type="button"
                    onClick={onToggle}
                    aria-label="Mở rộng thanh bên"
                    className={cn(
                      "flex h-9 w-full items-center justify-center gap-2 rounded-[var(--radius-md)]",
                      "text-[var(--text-muted)] transition-colors duration-[var(--duration-micro)]",
                      "hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
                    )}
                  >
                    <PanelLeftOpen size={16} aria-hidden="true" />
                  </button>
                }
              />
              <TooltipContent side="right" sideOffset={8}>
                Mở rộng thanh bên
              </TooltipContent>
            </Tooltip>
          ) : (
            <button
              type="button"
              onClick={onToggle}
              aria-label="Thu gọn thanh bên"
              className={cn(
                "flex h-9 w-full items-center justify-center gap-2 rounded-[var(--radius-md)]",
                "text-[var(--text-muted)] transition-colors duration-[var(--duration-micro)]",
                "hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
              )}
            >
              <PanelLeftClose size={16} aria-hidden="true" />
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
                className="text-xs font-medium"
              >
                Thu gọn
              </motion.span>
            </button>
          )}
        </div>
      </motion.aside>
    </TooltipProvider>
  );
}
