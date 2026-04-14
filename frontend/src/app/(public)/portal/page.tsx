"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { staggerContainer, slideUp } from "@/lib/motion";
import {
  Search,
  Building,
  Map,
  Briefcase,
  FileText,
  Leaf,
  Clock,
  Banknote,
  FolderOpen,
  Phone,
} from "lucide-react";

const TTHC_CARDS = [
  {
    code: "1.004415",
    name: "Cấp phép xây dựng",
    icon: Building,
    color: "text-blue-400",
    description:
      "Xin cấp giấy phép cho công trình xây dựng mới, sửa chữa, cải tạo",
    sla_days: 15,
    fee: 150000,
    doc_count: 7,
  },
  {
    code: "1.000046",
    name: "GCN quyền sử dụng đất",
    icon: Map,
    color: "text-green-400",
    description:
      "Cấp giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở",
    sla_days: 30,
    fee: 100000,
    doc_count: 5,
  },
  {
    code: "1.001757",
    name: "Đăng ký kinh doanh",
    icon: Briefcase,
    color: "text-purple-400",
    description:
      "Đăng ký thành lập doanh nghiệp, công ty TNHH, công ty cổ phần",
    sla_days: 3,
    fee: 50000,
    doc_count: 6,
  },
  {
    code: "1.000122",
    name: "Lý lịch tư pháp",
    icon: FileText,
    color: "text-amber-400",
    description: "Cấp phiếu lý lịch tư pháp cho cá nhân",
    sla_days: 10,
    fee: 200000,
    doc_count: 4,
  },
  {
    code: "2.002154",
    name: "Giấy phép môi trường",
    icon: Leaf,
    color: "text-emerald-400",
    description:
      "Xin cấp giấy phép môi trường cho dự án, cơ sở sản xuất",
    sla_days: 30,
    fee: 0,
    doc_count: 5,
  },
];

function formatFee(fee: number): string {
  if (fee === 0) return "Miễn phí";
  return fee.toLocaleString("vi-VN") + " đồng";
}

export default function CitizenPortal() {
  const [searchQuery, setSearchQuery] = useState("");
  const [trackingCode, setTrackingCode] = useState("");
  const router = useRouter();

  function handleTrack() {
    if (trackingCode.trim()) {
      router.push(`/track/${trackingCode.trim()}`);
    }
  }

  const filteredCards = TTHC_CARDS.filter(
    (t) =>
      !searchQuery ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.code.includes(searchQuery),
  );

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center px-4 py-20 text-center">
        <h1 className="text-4xl font-bold text-[var(--text-primary)]">
          Cổng dịch vụ công trực tuyến
        </h1>
        <p className="mt-3 max-w-xl text-lg text-[var(--text-secondary)]">
          Nộp hồ sơ thủ tục hành chính trực tuyến — không cần đến trực tiếp,
          theo dõi kết quả mọi lúc mọi nơi
        </p>

        {/* Search bar */}
        <div className="mt-8 flex w-full max-w-lg">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm thủ tục hành chính..."
              className="w-full rounded-l-lg border border-[var(--border-default)] bg-[var(--bg-surface)] py-3 pl-10 pr-4 text-sm outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
              aria-label="Tìm kiếm thủ tục"
            />
          </div>
          <button
            onClick={() => {
              /* Search is live-filtered below */
            }}
            className="rounded-r-lg bg-[var(--accent-primary)] px-6 py-3 font-medium text-white transition-opacity hover:opacity-90"
          >
            Tìm kiếm
          </button>
        </div>
      </section>

      {/* 5 TTHC Cards */}
      <motion.section
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="mx-auto grid max-w-5xl grid-cols-1 gap-4 px-4 pb-12 sm:grid-cols-2 lg:grid-cols-3"
      >
        {filteredCards.map((tthc) => {
          const Icon = tthc.icon;
          return (
            <motion.div
              key={tthc.code}
              variants={slideUp}
              className="flex flex-col rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 transition-shadow hover:shadow-md"
            >
              {/* Card header */}
              <div className="flex items-start gap-3">
                <Icon className={`mt-0.5 h-7 w-7 shrink-0 ${tthc.color}`} />
                <div className="min-w-0">
                  <p className="font-mono text-xs text-[var(--text-muted)]">
                    {tthc.code}
                  </p>
                  <h3 className="mt-0.5 font-bold text-[var(--text-primary)] leading-snug">
                    {tthc.name}
                  </h3>
                </div>
              </div>

              {/* Description */}
              <p className="mt-3 text-sm text-[var(--text-secondary)] leading-relaxed">
                {tthc.description}
              </p>

              {/* Metadata */}
              <div className="mt-4 space-y-1.5">
                <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <Clock className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
                  <span>
                    Thời gian xử lý:{" "}
                    <span className="font-medium text-[var(--text-primary)]">
                      {tthc.sla_days} ngày làm việc
                    </span>
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <Banknote className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
                  <span>
                    Lệ phí:{" "}
                    <span
                      className={`font-medium ${tthc.fee === 0 ? "text-[var(--accent-success)]" : "text-[var(--text-primary)]"}`}
                    >
                      {formatFee(tthc.fee)}
                    </span>
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <FolderOpen className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
                  <span>
                    Cần{" "}
                    <span className="font-medium text-[var(--text-primary)]">
                      {tthc.doc_count} thành phần hồ sơ
                    </span>
                  </span>
                </div>
              </div>

              {/* CTA */}
              <div className="mt-5">
                <button
                  onClick={() => router.push(`/submit/${tthc.code}`)}
                  className="w-full rounded-md bg-[var(--accent-primary)] py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] focus-visible:ring-offset-2"
                  aria-label={`Nộp hồ sơ ${tthc.name}`}
                >
                  Nộp hồ sơ
                </button>
              </div>
            </motion.div>
          );
        })}
      </motion.section>

      {/* Case Tracking Section */}
      <section className="mx-auto max-w-5xl px-4 pb-8">
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">
            Tra cứu hồ sơ
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Nhập mã hồ sơ để theo dõi tiến trình xử lý
          </p>
          <div className="mt-4 flex gap-2">
            <input
              type="text"
              value={trackingCode}
              onChange={(e) => setTrackingCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleTrack()}
              placeholder="Nhập mã hồ sơ (VD: HS-20260413-XXXX)"
              className="flex-1 rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-4 py-2.5 text-sm outline-none focus:border-[var(--accent-primary)]"
              aria-label="Mã hồ sơ"
            />
            <button
              onClick={handleTrack}
              className="rounded-md bg-[var(--accent-primary)] px-6 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              Tra cứu
            </button>
          </div>
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            Mã hồ sơ được cấp khi bạn nộp hồ sơ thành công. Ví dụ:
            HS-20260413-XXXX
          </p>
        </div>
      </section>

      {/* Support footer */}
      <section className="mx-auto max-w-5xl px-4 pb-16">
        <div className="flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-5 py-4">
          <Phone className="h-5 w-5 shrink-0 text-[var(--accent-primary)]" />
          <p className="text-sm text-[var(--text-secondary)]">
            Cần hỗ trợ? Liên hệ Tổng đài:{" "}
            <a
              href="tel:1900xxxx"
              className="font-semibold text-[var(--accent-primary)] hover:underline"
            >
              1900.xxxx
            </a>{" "}
            <span className="text-[var(--text-muted)]">(giờ hành chính)</span>
          </p>
        </div>
      </section>
    </div>
  );
}
