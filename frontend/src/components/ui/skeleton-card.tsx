import React from "react";
import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[var(--bg-surface-raised)]",
        className,
      )}
      style={style}
    />
  );
}

export function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4",
        className,
      )}
    >
      <Skeleton className="h-3 w-1/3" />
      <Skeleton className="mt-3 h-6 w-2/3" />
      <Skeleton className="mt-2 h-3 w-1/2" />
    </div>
  );
}

export function SkeletonKPICard() {
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-2 h-8 w-16" />
      <Skeleton className="mt-2 h-3 w-12" />
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <Skeleton className="h-3 w-32" />
      <div className="mt-4 flex items-end gap-2">
        {[60, 80, 45, 90, 70].map((h, i) => (
          <Skeleton key={i} className="flex-1" style={{ height: `${h}px` }} />
        ))}
      </div>
    </div>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3"
        >
          <Skeleton className="h-8 w-8 rounded-full" />
          <div className="flex-1">
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="mt-1.5 h-2 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
