"use client";

interface StepTTHCProps {
  tthcCode: string;
}

export function StepTTHC({ tthcCode }: StepTTHCProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-[var(--text-primary)]">
        Thủ tục hành chính
      </h2>
      <p className="mt-1 text-sm text-[var(--text-secondary)]">
        Mã thủ tục đã được chọn tự động
      </p>
      <div className="mt-4 rounded-md border border-[var(--accent-primary)]/30 bg-[var(--accent-primary)]/5 p-4">
        <p className="font-mono text-sm text-[var(--text-primary)]">{tthcCode}</p>
      </div>
    </div>
  );
}
