"use client";

import * as React from "react";
import { HelpCircle, Loader2 } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useFieldHelp } from "@/hooks/use-assistant";

interface SmartFieldHelperProps {
  tthcCode: string;
  fieldName: string;
}

export function SmartFieldHelper({ tthcCode, fieldName }: SmartFieldHelperProps) {
  const [open, setOpen] = React.useState(false);
  const { data, isLoading, error } = useFieldHelp(
    open ? tthcCode : "",
    open ? fieldName : "",
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <button
            type="button"
            aria-label={`Hướng dẫn trường ${fieldName}`}
            className="ml-1 inline-flex items-center justify-center rounded-full text-[var(--text-muted)] hover:text-[var(--accent-primary)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
          />
        }
      >
        <HelpCircle size={13} />
      </PopoverTrigger>
      <PopoverContent side="top" align="start" className="w-72 p-3 text-sm">
        {isLoading ? (
          <div className="flex items-center gap-2 text-[var(--text-muted)]">
            <Loader2 size={12} className="animate-spin" />
            <span className="text-xs">Đang tải hướng dẫn...</span>
          </div>
        ) : error ? (
          <p className="text-xs text-[var(--accent-destructive)]">
            Không thể tải hướng dẫn
          </p>
        ) : data ? (
          <div className="space-y-1.5">
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              {data.explanation}
            </p>
            {data.example_correct && (
              <p className="text-xs text-[var(--text-muted)]">
                Ví dụ đúng:{" "}
                <span className="font-mono font-medium text-[var(--accent-success)]">
                  {data.example_correct}
                </span>
              </p>
            )}
            {data.example_incorrect && (
              <p className="text-xs text-[var(--text-muted)]">
                Tránh:{" "}
                <span className="font-mono font-medium text-[var(--accent-destructive)]">
                  {data.example_incorrect}
                </span>
              </p>
            )}
            {data.related_law && (
              <p className="text-[10px] text-purple-600 border-t border-[var(--border-subtle)] pt-1.5">
                {data.related_law}
              </p>
            )}
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  );
}
