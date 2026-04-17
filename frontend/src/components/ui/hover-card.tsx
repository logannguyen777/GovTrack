"use client";

/**
 * HoverCard — lightweight wrapper that opens Popover on hover.
 * Shares PopoverContent's styling.
 */

import * as React from "react";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface HoverCardProps {
  children: React.ReactNode;
  openDelay?: number;
  closeDelay?: number;
}

function HoverCard({ children }: HoverCardProps) {
  const [open, setOpen] = React.useState(false);
  const enterTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleEnter() {
    if (leaveTimeout.current) clearTimeout(leaveTimeout.current);
    enterTimeout.current = setTimeout(() => setOpen(true), 250);
  }

  function handleLeave() {
    if (enterTimeout.current) clearTimeout(enterTimeout.current);
    leaveTimeout.current = setTimeout(() => setOpen(false), 100);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      {/* Spread hover handlers on children via wrapping div */}
      <div
        onMouseEnter={handleEnter}
        onMouseLeave={handleLeave}
        onFocus={handleEnter}
        onBlur={handleLeave}
      >
        {children}
      </div>
    </Popover>
  );
}

function HoverCardTrigger({
  asChild,
  children,
}: {
  asChild?: boolean;
  children: React.ReactNode;
}) {
  return (
    <PopoverTrigger
      render={asChild ? (children as React.ReactElement) : undefined}
    >
      {asChild ? undefined : children}
    </PopoverTrigger>
  );
}

function HoverCardContent({
  className,
  side = "top",
  align = "start",
  sideOffset = 4,
  alignOffset = 0,
  children,
  ...props
}: React.ComponentProps<typeof PopoverContent>) {
  return (
    <PopoverContent
      side={side}
      align={align}
      sideOffset={sideOffset}
      alignOffset={alignOffset}
      className={cn("w-72 p-4", className)}
      {...props}
    >
      {children}
    </PopoverContent>
  );
}

export { HoverCard, HoverCardTrigger, HoverCardContent };
