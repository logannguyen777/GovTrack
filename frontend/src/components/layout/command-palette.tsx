"use client";

import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  Inbox,
  ShieldCheck,
  FileText,
  GitBranch,
  Lock,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

// ---------------------------------------------------------------------------
// Nav items — must match sidebar.tsx definitions
// ---------------------------------------------------------------------------

const NAV_ITEMS = [
  { label: "Bảng điều hành", href: "/dashboard", icon: LayoutDashboard, keywords: "dashboard" },
  { label: "Tiếp nhận hồ sơ", href: "/intake",    icon: Upload,          keywords: "intake upload nop" },
  { label: "Hồ sơ đến",       href: "/inbox",     icon: Inbox,           keywords: "inbox cases ho so" },
  { label: "Tuân thủ",          href: "/compliance", icon: ShieldCheck,  keywords: "compliance tuan thu kiem tra" },
  { label: "Tài liệu",         href: "/documents", icon: FileText,        keywords: "documents tai lieu" },
  { label: "Theo dõi AI",      href: "/trace",     icon: GitBranch,       keywords: "trace theo doi ai agent" },
  { label: "Bảo mật",          href: "/security",  icon: Lock,            keywords: "security bao mat" },
] as const;

// ---------------------------------------------------------------------------
// CommandPalette
// ---------------------------------------------------------------------------

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();

  function handleSelect(href: string) {
    router.push(href);
    onOpenChange(false);
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Bảng lệnh GovFlow"
      description="Tìm kiếm trang, hồ sơ, tài liệu..."
    >
      <CommandInput
        placeholder="Tìm kiếm trang..."
        aria-label="Tìm kiếm bảng lệnh"
      />

      <CommandList>
        <CommandEmpty
          style={{ color: "var(--text-muted)" }}
        >
          Không tìm thấy kết quả nào.
        </CommandEmpty>

        {/* Navigation group */}
        <CommandGroup heading="Điều hướng">
          {NAV_ITEMS.map(({ label, href, icon: Icon, keywords }) => (
            <CommandItem
              key={href}
              value={`${label} ${keywords}`}
              onSelect={() => handleSelect(href)}
              className="gap-3"
              aria-label={`Đi đến ${label}`}
            >
              <Icon
                size={16}
                aria-hidden="true"
                style={{ color: "var(--text-muted)" }}
              />
              <span style={{ color: "var(--text-primary)" }}>{label}</span>
              <span
                className="ml-auto text-[10px] font-mono"
                style={{ color: "var(--text-muted)" }}
              >
                {href}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>

      {/* Footer hint */}
      <div
        className="flex items-center gap-3 border-t px-3 py-2"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <span
          className="text-[10px]"
          style={{ color: "var(--text-muted)" }}
        >
          <kbd
            className="rounded px-1 py-0.5 font-mono text-[9px]"
            style={{
              backgroundColor: "var(--bg-surface-raised)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            ↵
          </kbd>{" "}
          chọn
        </span>
        <span
          className="text-[10px]"
          style={{ color: "var(--text-muted)" }}
        >
          <kbd
            className="rounded px-1 py-0.5 font-mono text-[9px]"
            style={{
              backgroundColor: "var(--bg-surface-raised)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            Esc
          </kbd>{" "}
          đóng
        </span>
      </div>
    </CommandDialog>
  );
}
