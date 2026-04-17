"use client";

import { use, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Copy,
  CheckCheck,
  Download,
  ExternalLink,
  Bell,
  Mail,
  Smartphone,
  BellRing,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function addWorkdays(date: Date, days: number): Date {
  const result = new Date(date);
  let added = 0;
  while (added < days) {
    result.setDate(result.getDate() + 1);
    const dow = result.getDay();
    if (dow !== 0 && dow !== 6) added++;
  }
  return result;
}

function formatVNDate(d: Date): string {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

const NOTIF_CHANNEL_KEY = "govflow-notif-channel";

type Channel = "sms" | "email" | "vneid" | "all";

const CHANNELS: { key: Channel; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { key: "sms", label: "SMS", icon: Bell },
  { key: "email", label: "Email", icon: Mail },
  { key: "vneid", label: "VNeID Push", icon: Smartphone },
  { key: "all", label: "Tất cả", icon: BellRing },
];

// QR placeholder SVG encoding a mock tracking URL
function ReceiptQR({ caseCode }: { caseCode: string }) {
  return (
    <svg
      width="120"
      height="120"
      viewBox="0 0 120 120"
      className="rounded-lg border border-[var(--border-subtle)] bg-white p-2"
      aria-label={`Mã QR tra cứu hồ sơ ${caseCode}`}
    >
      {/* Finder patterns */}
      <rect x="8" y="8" width="30" height="30" rx="2" fill="none" stroke="#111" strokeWidth="3" />
      <rect x="15" y="15" width="16" height="16" rx="1" fill="#111" />
      <rect x="82" y="8" width="30" height="30" rx="2" fill="none" stroke="#111" strokeWidth="3" />
      <rect x="89" y="15" width="16" height="16" rx="1" fill="#111" />
      <rect x="8" y="82" width="30" height="30" rx="2" fill="none" stroke="#111" strokeWidth="3" />
      <rect x="15" y="89" width="16" height="16" rx="1" fill="#111" />
      {/* Data modules */}
      {Array.from({ length: 12 }, (_, col) =>
        Array.from({ length: 12 }, (_, row) => {
          const x = 45 + col * 5;
          const y = 45 + row * 5;
          return Math.sin(col * 1.3 + row * 0.9 + caseCode.charCodeAt(0) * 0.1) > 0.2 ? (
            <rect key={`${col}-${row}`} x={x} y={y} width="4" height="4" fill="#111" />
          ) : null;
        })
      )}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Receipt page
// ---------------------------------------------------------------------------

function ReceiptContent({
  caseCode,
  tthcCode,
}: {
  caseCode: string;
  tthcCode: string;
}) {
  const router = useRouter();
  const [copied, setCopied] = useState(false);
  const [channel, setChannel] = useState<Channel>(() => {
    if (typeof window !== "undefined") {
      return (localStorage.getItem(NOTIF_CHANNEL_KEY) as Channel) ?? "vneid";
    }
    return "vneid";
  });

  const slaDate = addWorkdays(new Date(), 10);
  const slaLabel = `Dự kiến trả kết quả trước 17:00 ngày ${formatVNDate(slaDate)}`;

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(caseCode);
    setCopied(true);
    toast.success("Đã sao chép mã hồ sơ");
    setTimeout(() => setCopied(false), 2000);
  }, [caseCode]);

  function handleChannelChange(ch: Channel) {
    setChannel(ch);
    localStorage.setItem(NOTIF_CHANNEL_KEY, ch);
    toast.success(`Sẽ nhận thông báo qua: ${CHANNELS.find((c) => c.key === ch)?.label}`);
  }

  function handleDownloadPDF() {
    toast.info("Đang tạo PDF biên nhận...", { duration: 3000 });
    setTimeout(() => {
      toast.success("PDF đã sẵn sàng (mock)");
    }, 2500);
  }

  const trackingUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/track/${caseCode}`
      : `/track/${caseCode}`;

  const decoded = decodeURIComponent(tthcCode);

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* Success header */}
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1] }}
        className="mb-8 text-center"
      >
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--accent-success)]/15">
          <CheckCheck size={32} className="text-[var(--accent-success)]" />
        </div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">
          Nộp hồ sơ thành công
        </h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Hồ sơ của bạn đã được tiếp nhận theo quy định tại NĐ 61/2018/NĐ-CP
        </p>
      </motion.div>

      {/* Receipt card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1, ease: [0.25, 1, 0.5, 1] }}
        className="relative overflow-hidden rounded-2xl border-2 border-[var(--border-default)] bg-[var(--bg-surface)] shadow-lg"
      >
        {/* Watermark */}
        <div
          className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-[0.03]"
          aria-hidden="true"
        >
          <span className="rotate-[-30deg] text-[8rem] font-black tracking-widest text-[var(--text-primary)]">
            BIÊN NHẬN
          </span>
        </div>

        {/* Receipt header stripe */}
        <div className="relative border-b border-[var(--border-subtle)] bg-gradient-to-r from-blue-600 to-indigo-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-100">
                Cổng Dịch vụ công · GovFlow
              </p>
              <p className="mt-0.5 text-base font-bold text-white">
                Biên nhận điện tử
              </p>
            </div>
            <div className="text-right text-xs text-blue-100">
              <p>NĐ 61/2018/NĐ-CP</p>
              <p>NĐ 42/2022/NĐ-CP</p>
            </div>
          </div>
        </div>

        <div className="relative px-6 py-5">
          {/* Case code + QR row */}
          <div className="flex items-start justify-between gap-6">
            <div className="flex-1">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                Mã hồ sơ
              </p>
              <div className="mt-2 flex items-center gap-3">
                <p className="font-mono text-2xl font-black tracking-wide text-[var(--text-primary)]">
                  {caseCode}
                </p>
                <button
                  type="button"
                  onClick={() => void handleCopy()}
                  aria-label="Sao chép mã hồ sơ"
                  className="flex items-center gap-1.5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)]"
                >
                  {copied ? (
                    <>
                      <CheckCheck size={13} className="text-[var(--accent-success)]" />
                      Đã sao chép
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      Copy mã
                    </>
                  )}
                </button>
              </div>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Giữ mã này để tra cứu kết quả xử lý
              </p>
            </div>
            <div className="shrink-0">
              <ReceiptQR caseCode={caseCode} />
              <p className="mt-1 text-center text-[10px] text-[var(--text-muted)]">
                Quét để theo dõi
              </p>
            </div>
          </div>

          {/* Divider */}
          <div className="my-5 border-t border-dashed border-[var(--border-subtle)]" />

          {/* Receipt details */}
          <dl className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <dt className="text-sm text-[var(--text-secondary)]">Thủ tục hành chính</dt>
              <dd className="text-right text-sm font-medium text-[var(--text-primary)]">
                TTHC {decoded}
              </dd>
            </div>

            <div className="flex items-start justify-between gap-2">
              <dt className="text-sm text-[var(--text-secondary)]">Cơ quan xử lý</dt>
              <dd className="text-right text-sm font-medium text-[var(--text-primary)]">
                Sở Xây dựng TP. Hà Nội
              </dd>
            </div>

            <div className="flex items-start justify-between gap-2">
              <dt className="text-sm text-[var(--text-secondary)]">Ngày tiếp nhận</dt>
              <dd className="text-right text-sm font-medium text-[var(--text-primary)]">
                {formatVNDate(new Date())}
              </dd>
            </div>

            <div className="rounded-lg border border-[var(--accent-primary)]/20 bg-[var(--accent-primary)]/5 px-4 py-3">
              <p className="text-sm font-semibold text-[var(--accent-primary)]">
                {slaLabel}
              </p>
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                Theo quy định tại NĐ 61/2018 và TTHCSpec thủ tục này (10 ngày làm việc)
              </p>
            </div>
          </dl>

          {/* Divider */}
          <div className="my-5 border-t border-dashed border-[var(--border-subtle)]" />

          {/* Legal basis */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Căn cứ pháp lý
            </p>
            <ul className="space-y-1.5 text-xs text-[var(--text-secondary)]">
              {[
                "NĐ 61/2018/NĐ-CP — Một cửa, một cửa liên thông",
                "NĐ 42/2022/NĐ-CP — Cung cấp dịch vụ công trực tuyến",
                "Luật Xây dựng 2014 (sửa đổi 2020) — Cấp phép xây dựng",
              ].map((law) => (
                <li key={law} className="flex items-start gap-1.5">
                  <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent-primary)]" />
                  {law}
                </li>
              ))}
            </ul>
          </div>

          {/* Divider */}
          <div className="my-5 border-t border-dashed border-[var(--border-subtle)]" />

          {/* Notification channel selector */}
          <div>
            <p className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
              Nhận thông báo cập nhật qua:
            </p>
            <div className="flex flex-wrap gap-2">
              {CHANNELS.map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleChannelChange(key)}
                  aria-pressed={channel === key}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    channel === key
                      ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                      : "border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--accent-primary)]/50 hover:text-[var(--text-primary)]"
                  }`}
                >
                  <Icon size={12} />
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-[var(--text-muted)]">
              Lựa chọn lưu tự động · Chỉ nhận thông báo liên quan đến hồ sơ này
            </p>
          </div>
        </div>

        {/* Receipt footer */}
        <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-6 py-3">
          <p className="text-center text-[10px] text-[var(--text-muted)]">
            Đường dẫn tra cứu:{" "}
            <a
              href={trackingUrl}
              className="font-mono text-[var(--accent-primary)] hover:underline"
            >
              {trackingUrl}
            </a>
          </p>
        </div>
      </motion.div>

      {/* Action buttons */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.25 }}
        className="mt-6 flex flex-wrap justify-center gap-3"
      >
        <button
          type="button"
          onClick={() => void handleCopy()}
          className="flex items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-5 py-2.5 text-sm font-medium text-[var(--text-secondary)] shadow-sm transition-colors hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)]"
        >
          {copied ? <CheckCheck size={15} className="text-[var(--accent-success)]" /> : <Copy size={15} />}
          Copy mã
        </button>

        <button
          type="button"
          onClick={handleDownloadPDF}
          className="flex items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-5 py-2.5 text-sm font-medium text-[var(--text-secondary)] shadow-sm transition-colors hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)]"
        >
          <Download size={15} />
          Tải PDF biên nhận
        </button>

        <button
          type="button"
          onClick={() => router.push(`/track/${caseCode}`)}
          className="flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
          style={{ background: "var(--accent-primary)" }}
        >
          <ExternalLink size={15} />
          Theo dõi hồ sơ
        </button>
      </motion.div>

      <p className="mt-6 text-center text-xs text-[var(--text-muted)]">
        Lưu trang này hoặc chụp màn hình làm bằng chứng tiếp nhận điện tử.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page (Next.js 15 — params + searchParams are Promises)
// ---------------------------------------------------------------------------

export default function ReceiptPage({
  params,
  searchParams,
}: {
  params: Promise<{ tthc_code: string }>;
  searchParams: Promise<{ case?: string }>;
}) {
  const { tthc_code } = use(params);
  const { case: caseCode } = use(searchParams);

  const router = useRouter();

  if (!caseCode) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-[var(--text-secondary)]">
          Không tìm thấy mã hồ sơ. Vui lòng{" "}
          <button
            type="button"
            onClick={() => router.push("/portal")}
            className="text-[var(--accent-primary)] underline"
          >
            quay lại trang chủ
          </button>
          .
        </p>
      </div>
    );
  }

  return <ReceiptContent caseCode={caseCode} tthcCode={tthc_code} />;
}
