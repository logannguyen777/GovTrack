"use client";

import { usePathname } from "next/navigation";
import {
  Search,
  Bell,
  Sun,
  Moon,
  LogOut,
  ChevronRight,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useNotificationStore } from "@/lib/store";
import { useTheme } from "@/components/providers/theme-provider";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Route label map for breadcrumbs
// ---------------------------------------------------------------------------

const ROUTE_LABELS: Record<string, string> = {
  dashboard:  "Bảng điều hành",
  intake:     "Tiếp nhận hồ sơ",
  inbox:      "Hồ sơ đến",
  compliance: "Tuân thủ",
  documents:  "Tài liệu",
  trace:      "Theo dõi AI",
  security:   "Bảo mật",
};

// ---------------------------------------------------------------------------
// Breadcrumb derived from pathname
// ---------------------------------------------------------------------------

function Breadcrumb({ pathname }: { pathname: string }) {
  // Strip leading slash, split into segments, filter empty
  const segments = pathname.replace(/^\//, "").split("/").filter(Boolean);

  if (segments.length === 0) {
    return (
      <span
        className="text-sm font-medium"
        style={{ color: "var(--text-primary)" }}
      >
        GovFlow
      </span>
    );
  }

  return (
    <nav aria-label="Đường dẫn" className="flex items-center gap-1">
      <span
        className="text-sm"
        style={{ color: "var(--text-muted)" }}
      >
        GovFlow
      </span>

      {segments.map((seg, idx) => {
        const isLast = idx === segments.length - 1;
        // Use the label map for known route segments; format unknown ones
        const label =
          ROUTE_LABELS[seg] ??
          seg
            .replace(/-/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase());

        return (
          <span key={seg + idx} className="flex items-center gap-1">
            <ChevronRight
              size={12}
              aria-hidden="true"
              style={{ color: "var(--text-muted)" }}
            />
            <span
              className="text-sm font-medium"
              style={{
                color: isLast
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
              }}
              aria-current={isLast ? "page" : undefined}
            >
              {label}
            </span>
          </span>
        );
      })}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Notification popover
// ---------------------------------------------------------------------------

const NOTIF_TYPE_COLORS: Record<string, string> = {
  info:    "var(--accent-info)",
  warning: "var(--accent-warning)",
  error:   "var(--accent-destructive, var(--accent-error))",
  success: "var(--accent-success)",
};

function NotificationPopover() {
  const { notifications, unreadCount, markRead, markAllRead } =
    useNotificationStore();

  return (
    <Popover>
      <PopoverTrigger
        aria-label={
          unreadCount > 0
            ? `Thông báo — ${unreadCount} chưa đọc`
            : "Thông báo"
        }
        className={cn(
          "relative flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)]",
          "text-[var(--text-muted)] transition-colors duration-[var(--duration-micro)]",
          "hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
        )}
      >
        <Bell size={18} aria-hidden="true" />
        {unreadCount > 0 && (
          <span
            aria-hidden="true"
            className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full px-0.5 text-[9px] font-bold text-white"
            style={{ backgroundColor: "var(--accent-primary)" }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-80 p-0 overflow-hidden"
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3 border-b"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <span
            className="text-sm font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            Thông báo
            {unreadCount > 0 && (
              <span
                className="ml-2 rounded-full px-1.5 py-0.5 text-[10px] font-bold"
                style={{
                  backgroundColor: "var(--accent-primary)",
                  color: "white",
                }}
              >
                {unreadCount}
              </span>
            )}
          </span>
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={markAllRead}
              className="text-xs font-medium transition-colors duration-[var(--duration-micro)]"
              style={{ color: "var(--accent-primary)" }}
            >
              Đánh dấu tất cả đã đọc
            </button>
          )}
        </div>

        {/* Notification list */}
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 ? (
            <div
              className="flex flex-col items-center gap-2 py-8 text-center"
              style={{ color: "var(--text-muted)" }}
            >
              <Bell size={24} aria-hidden="true" />
              <p className="text-sm">Không có thông báo nào</p>
            </div>
          ) : (
            notifications.map((n) => (
              <button
                type="button"
                key={n.id}
                onClick={() => markRead(n.id)}
                className={cn(
                  "w-full px-4 py-3 text-left transition-colors duration-[var(--duration-micro)]",
                  "hover:bg-[var(--bg-surface-raised)]",
                  "border-b last:border-b-0",
                  !n.read && "bg-[var(--bg-surface-raised)]",
                )}
                style={{ borderColor: "var(--border-subtle)" }}
              >
                <div className="flex items-start gap-2.5">
                  {/* Type indicator dot */}
                  <span
                    aria-hidden="true"
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor: NOTIF_TYPE_COLORS[n.type] ?? "var(--text-muted)",
                      opacity: n.read ? 0.4 : 1,
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <p
                      className="truncate text-xs font-semibold"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {n.title}
                    </p>
                    <p
                      className="mt-0.5 line-clamp-2 text-[11px]"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {n.message}
                    </p>
                    <p
                      className="mt-1 text-[10px]"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {new Date(n.timestamp).toLocaleString("vi-VN", {
                        day: "2-digit",
                        month: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// Theme toggle button
// ---------------------------------------------------------------------------

function ThemeToggle() {
  const { resolved, setTheme } = useTheme();

  return (
    <button
      type="button"
      aria-label={
        resolved === "dark" ? "Chuyển sang chế độ sáng" : "Chuyển sang chế độ tối"
      }
      onClick={() => setTheme(resolved === "dark" ? "light" : "dark")}
      className={cn(
        "flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)]",
        "text-[var(--text-muted)] transition-colors duration-[var(--duration-micro)]",
        "hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
      )}
    >
      {resolved === "dark" ? (
        <Sun size={18} aria-hidden="true" />
      ) : (
        <Moon size={18} aria-hidden="true" />
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// User dropdown
// ---------------------------------------------------------------------------

const ROLE_LABELS: Record<string, string> = {
  admin:           "Quản trị viên",
  leader:          "Lãnh đạo",
  officer:         "Cán bộ",
  staff_intake:    "Cán bộ tiếp nhận",
  staff_processor: "Cán bộ xử lý",
  legal:           "Pháp chế",
  security:        "An ninh",
  public_viewer:   "Xem công khai",
  citizen:         "Công dân",
};

function UserDropdown() {
  const { user, logout } = useAuth();

  if (!user) return null;

  const initials = user.username.slice(0, 2).toUpperCase();
  const roleLabel = ROLE_LABELS[user.role] ?? user.role;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Tài khoản: ${user.username}`}
        className={cn(
          "flex items-center gap-2 rounded-[var(--radius-md)] px-2 py-1.5",
          "text-[var(--text-muted)] transition-colors duration-[var(--duration-micro)]",
          "hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
        )}
      >
        <Avatar size="sm">
          <AvatarFallback
            className="text-[10px] font-bold text-white"
            style={{ backgroundColor: "var(--accent-primary)" }}
          >
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="hidden flex-col items-start sm:flex">
          <span
            className="text-xs font-semibold leading-none"
            style={{ color: "var(--text-primary)" }}
          >
            {user.username}
          </span>
          <span
            className="text-[10px] leading-none mt-0.5"
            style={{ color: "var(--text-muted)" }}
          >
            {roleLabel}
          </span>
        </div>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" side="bottom" sideOffset={8}>
        {/* Identity header */}
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <div className="flex flex-col gap-0.5">
              <span style={{ color: "var(--text-primary)" }}>{user.username}</span>
              <span
                className="text-[10px] font-normal"
                style={{ color: "var(--text-muted)" }}
              >
                {roleLabel}
              </span>
            </div>
          </DropdownMenuLabel>
        </DropdownMenuGroup>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          style={{ color: "var(--text-secondary)" }}
        >
          <UserIcon size={14} aria-hidden="true" />
          Hồ sơ cá nhân
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          variant="destructive"
          onClick={logout}
        >
          <LogOut size={14} aria-hidden="true" />
          Đăng xuất
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ---------------------------------------------------------------------------
// TopBar
// ---------------------------------------------------------------------------

interface TopBarProps {
  onCommandOpen: () => void;
}

export function TopBar({ onCommandOpen }: TopBarProps) {
  const pathname = usePathname();

  return (
    <header
      className="flex h-14 shrink-0 items-center justify-between border-b px-4 gap-4"
      style={{
        backgroundColor: "var(--bg-surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* Left: breadcrumb */}
      <div className="min-w-0 flex-1">
        <Breadcrumb pathname={pathname} />
      </div>

      {/* Right: action buttons */}
      <div className="flex items-center gap-1 shrink-0">
        {/* Search / command palette trigger */}
        <button
          type="button"
          aria-label="Tìm kiếm (⌘K)"
          onClick={onCommandOpen}
          className={cn(
            "flex h-9 items-center gap-2 rounded-[var(--radius-md)] px-3",
            "border text-sm transition-colors duration-[var(--duration-micro)]",
            "text-[var(--text-muted)]",
            "hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
          )}
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <Search size={14} aria-hidden="true" />
          <span className="hidden sm:inline text-xs">Tìm kiếm</span>
          <kbd
            aria-hidden="true"
            className="hidden sm:inline-flex items-center gap-0.5 rounded px-1 py-0.5 text-[10px] font-mono"
            style={{
              backgroundColor: "var(--bg-surface-raised)",
              color: "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            ⌘K
          </kbd>
        </button>

        {/* Notification bell */}
        <NotificationPopover />

        {/* Demo mode badge */}
        {process.env.NEXT_PUBLIC_DEMO_MODE === "true" && (
          <span className="rounded-sm bg-[var(--accent-warning)] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-black">
            DEMO
          </span>
        )}

        {/* Theme toggle */}
        <ThemeToggle />

        {/* User dropdown */}
        <UserDropdown />
      </div>
    </header>
  );
}
