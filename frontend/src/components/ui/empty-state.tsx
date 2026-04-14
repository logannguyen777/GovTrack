import { type LucideIcon, Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 text-center">
      <Icon className="h-10 w-10 text-[var(--text-muted)]" />
      <h3 className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
        {title}
      </h3>
      {description && (
        <p className="mt-1 text-xs text-[var(--text-muted)]">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-3 rounded-md bg-[var(--accent-primary)] px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
