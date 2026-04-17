"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { staggerContainer, slideUp } from "@/lib/motion";
import {
  Sparkles,
  Building,
  Map,
  Briefcase,
  FileText,
  Leaf,
  Clock,
  Banknote,
  FolderOpen,
  Phone,
  Baby,
  Heart,
  CreditCard,
} from "lucide-react";
import { QuickIntentChip } from "@/components/assistant/quick-intent-chip";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { useIntent } from "@/hooks/use-assistant";
import { usePublicStats } from "@/hooks/use-public";
import { QwenPitchSection } from "@/components/portal";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

// ---------------------------------------------------------------------------
// Life-event data
// ---------------------------------------------------------------------------

const LIFE_EVENTS = [
  {
    key: "build",
    icon: Building,
    title: "Xây nhà",
    description: "Xin giấy phép xây dựng, sửa chữa, cải tạo công trình",
    tthcCode: "1.004415",
    color: "text-blue-500",
    bg: "from-blue-50 to-indigo-50 dark:from-blue-950/40 dark:to-indigo-950/40",
    border: "border-blue-100 dark:border-blue-900",
  },
  {
    key: "business",
    icon: Briefcase,
    title: "Mở doanh nghiệp",
    description: "Đăng ký thành lập doanh nghiệp, công ty TNHH, hộ kinh doanh",
    tthcCode: "1.001757",
    color: "text-purple-500",
    bg: "from-purple-50 to-violet-50 dark:from-purple-950/40 dark:to-violet-950/40",
    border: "border-purple-100 dark:border-purple-900",
  },
  {
    key: "birth",
    icon: Baby,
    title: "Sinh con",
    description: "Đăng ký khai sinh, hộ khẩu cho trẻ em mới sinh",
    tthcCode: "1.000046",
    color: "text-emerald-500",
    bg: "from-emerald-50 to-teal-50 dark:from-emerald-950/40 dark:to-teal-950/40",
    border: "border-emerald-100 dark:border-emerald-900",
  },
  {
    key: "marriage",
    icon: Heart,
    title: "Kết hôn",
    description: "Đăng ký kết hôn, thay đổi thông tin hộ tịch",
    tthcCode: "1.000122",
    color: "text-pink-500",
    bg: "from-pink-50 to-rose-50 dark:from-pink-950/40 dark:to-rose-950/40",
    border: "border-pink-100 dark:border-pink-900",
  },
  {
    key: "cccd",
    icon: CreditCard,
    title: "Đổi CCCD",
    description: "Cấp mới, đổi thẻ căn cước công dân gắn chip",
    tthcCode: "1.000122",
    color: "text-amber-500",
    bg: "from-amber-50 to-yellow-50 dark:from-amber-950/40 dark:to-yellow-950/40",
    border: "border-amber-100 dark:border-amber-900",
  },
  {
    key: "criminal",
    icon: FileText,
    title: "Lý lịch tư pháp",
    description: "Cấp phiếu lý lịch tư pháp số 1 và số 2",
    tthcCode: "1.000122",
    color: "text-slate-500",
    bg: "from-slate-50 to-gray-50 dark:from-slate-950/40 dark:to-gray-950/40",
    border: "border-slate-100 dark:border-slate-900",
  },
] as const;

// ---------------------------------------------------------------------------
// LifeEventTiles
// ---------------------------------------------------------------------------

function LifeEventTiles({ onNavigate }: { onNavigate: (code: string) => void }) {
  return (
    <section className="mx-auto max-w-5xl px-4 pt-10 pb-2">
      <div className="mb-5 flex items-center gap-2">
        <h2 className="text-xl font-bold text-[var(--text-primary)]">
          Tôi cần làm gì?
        </h2>
        <span className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-0.5 text-xs text-[var(--text-muted)]">
          Chọn sự kiện cuộc sống
        </span>
      </div>
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
      >
        {LIFE_EVENTS.map((ev) => {
          const Icon = ev.icon;
          return (
            <motion.button
              key={ev.key}
              variants={slideUp}
              type="button"
              onClick={() => onNavigate(ev.tthcCode)}
              aria-label={`${ev.title} — ${ev.description}`}
              whileHover={{ y: -4, transition: { duration: 0.15 } }}
              whileTap={{ scale: 0.98 }}
              className={`group flex items-start gap-4 rounded-xl border bg-gradient-to-br p-5 text-left shadow-sm transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] focus-visible:ring-offset-2 ${ev.bg} ${ev.border}`}
            >
              <div
                className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/80 shadow-sm dark:bg-black/20 ${ev.color}`}
              >
                <Icon size={20} />
              </div>
              <div className="min-w-0">
                <p className={`font-bold text-[var(--text-primary)] text-base leading-tight ${ev.color}`}>
                  {ev.title}
                </p>
                <p className="mt-1 text-sm text-[var(--text-secondary)] leading-snug">
                  {ev.description}
                </p>
              </div>
            </motion.button>
          );
        })}
      </motion.div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

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
    required_components: [
      "Đơn đề nghị cấp phép (theo mẫu)",
      "Bản vẽ thiết kế (bản vẽ mặt bằng, mặt đứng, mặt cắt)",
      "Giấy chứng nhận quyền sử dụng đất",
      "Tờ trình thẩm định thiết kế (nếu có)",
      "Hợp đồng thiết kế",
      "Ảnh chụp thực địa",
      "Bản sao CCCD/CMND",
    ],
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
    required_components: [
      "Đơn đăng ký cấp GCN (theo mẫu)",
      "Tờ khai đăng ký đất đai",
      "Giấy tờ về quyền sở hữu đất",
      "Sơ đồ thửa đất (nếu chưa có bản đồ địa chính)",
      "Bản sao CCCD/CMND",
    ],
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
    required_components: [
      "Giấy đề nghị đăng ký doanh nghiệp",
      "Điều lệ công ty",
      "Danh sách thành viên/cổ đông",
      "Bản sao CCCD/hộ chiếu của người đại diện",
      "Văn bản uỷ quyền (nếu có)",
      "Chứng chỉ hành nghề (nếu cần)",
    ],
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
    required_components: [
      "Tờ khai yêu cầu cấp phiếu",
      "Bản sao CCCD/CMND",
      "Bản sao hộ khẩu (hoặc giấy tạm trú)",
      "Ảnh thẻ 3x4",
    ],
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
    required_components: [
      "Văn bản đề nghị cấp giấy phép môi trường",
      "Báo cáo đánh giá tác động môi trường (ĐTM)",
      "Hồ sơ pháp lý dự án",
      "Bản đồ vị trí dự án",
      "Cam kết thực hiện các biện pháp bảo vệ môi trường",
    ],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatFee(fee: number): string {
  if (fee === 0) return "Miễn phí";
  return fee.toLocaleString("vi-VN") + " đồng";
}

// ---------------------------------------------------------------------------
// IntentResultCard
// ---------------------------------------------------------------------------

function IntentResultCard({
  intent,
  onSubmit,
}: {
  intent: ReturnType<typeof useIntent>["data"];
  onSubmit: (code: string) => void;
}) {
  if (!intent) return null;
  const { primary, alternatives } = intent;

  if (!primary && (!alternatives || alternatives.length === 0)) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mt-8 mx-auto max-w-2xl rounded-2xl border p-5 text-left"
        style={{
          background: "var(--gradient-qwen-soft)",
          borderColor: "oklch(0.65 0.15 280 / 0.3)",
        }}
      >
        <div className="flex items-start gap-3">
          <Sparkles size={18} className="mt-0.5 shrink-0 text-purple-600" />
          <p className="text-sm text-[var(--text-secondary)]">
            AI chưa nhận diện được thủ tục phù hợp. Vui lòng mô tả cụ thể hơn hoặc chọn từ danh sách bên dưới.
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mt-8 mx-auto max-w-2xl rounded-2xl border p-5 text-left"
      style={{
        background: "var(--gradient-qwen-soft)",
        borderColor: "oklch(0.65 0.15 280 / 0.3)",
      }}
    >
      <div className="flex items-start gap-3">
        <Sparkles size={18} className="mt-0.5 shrink-0 text-purple-600" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            AI gợi ý thủ tục phù hợp nhất:
          </p>
          {primary && (
            <div className="mt-2 flex items-center gap-3">
              <div className="flex-1">
                <p className="text-base font-bold text-purple-700">{primary.name}</p>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  {primary.department ? `${primary.department} · ` : ""}
                  {primary.sla_days ? `${primary.sla_days} ngày · ` : ""}
                  Độ phù hợp:{" "}
                  <span className="font-semibold text-[var(--accent-success)]">
                    {Math.round(primary.confidence * 100)}%
                  </span>
                </p>
              </div>
              <button
                type="button"
                onClick={() => onSubmit(primary.tthc_code)}
                className="shrink-0 rounded-xl px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
                style={{ background: "var(--gradient-qwen)" }}
              >
                Nộp ngay
              </button>
            </div>
          )}

          {alternatives && alternatives.length > 0 && (
            <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
              <p className="text-xs text-[var(--text-muted)] mb-1.5">Có thể phù hợp:</p>
              <div className="flex flex-wrap gap-1.5">
                {alternatives.map((a) => (
                  <button
                    key={a.tthc_code}
                    type="button"
                    onClick={() => onSubmit(a.tthc_code)}
                    className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1 text-xs text-[var(--text-secondary)] hover:border-purple-300 hover:text-purple-700 transition-colors"
                  >
                    {a.name}{" "}
                    <span className="text-[10px] opacity-70">
                      {Math.round(a.confidence * 100)}%
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Tooltip for TTHC required_components (plain text list)
// ---------------------------------------------------------------------------

function TTHCHoverCard({
  tthc,
  children,
}: {
  tthc: (typeof TTHC_CARDS)[0];
  children: React.ReactNode;
}) {
  const tipContent = tthc.required_components.join(" · ");
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger render={<span>{children}</span>} />
        <TooltipContent side="top" className="max-w-xs text-left">
          <p className="font-semibold text-xs mb-1">Thành phần hồ sơ:</p>
          <p className="text-xs leading-relaxed">{tipContent}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CitizenPortal() {
  const [intentText, setIntentText] = useState("");
  const [trackingCode, setTrackingCode] = useState("");
  const router = useRouter();
  const intentMutation = useIntent();
  const { data: stats } = usePublicStats();

  function handleTrack() {
    if (trackingCode.trim()) {
      router.push(`/track/${trackingCode.trim()}`);
    }
  }

  // Demo shortcut — jumps straight to the pre-seeded hero case
  function handleViewDemoCase() {
    router.push("/track/HS-20260101-CASE0001");
  }

  async function handleAISearch() {
    if (!intentText.trim()) return;
    await intentMutation.mutateAsync(intentText);
  }

  function handleIntentKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleAISearch();
    }
  }

  function handleChipClick(text: string) {
    setIntentText(text);
    void intentMutation.mutateAsync(text);
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "GovernmentOrganization",
    name: "GovFlow — Hệ thống xử lý TTHC thông minh",
    url: process.env.NEXT_PUBLIC_SITE_URL || "https://govflow.vn",
    description:
      "Hệ thống xử lý thủ tục hành chính công ứng dụng AI Qwen3 và đồ thị tri thức tại Việt Nam.",
    areaServed: "VN",
    availableLanguage: "vi",
    hasOfferCatalog: {
      "@type": "OfferCatalog",
      name: "Dịch vụ hành chính công",
      itemListElement: [
        {
          "@type": "GovernmentService",
          name: "Cấp phép xây dựng",
          serviceType: "Thủ tục hành chính công",
          provider: { "@type": "GovernmentOrganization", name: "GovFlow" },
        },
        {
          "@type": "GovernmentService",
          name: "Đăng ký kinh doanh",
          serviceType: "Thủ tục hành chính công",
          provider: { "@type": "GovernmentOrganization", name: "GovFlow" },
        },
        {
          "@type": "GovernmentService",
          name: "Cấp giấy chứng nhận quyền sử dụng đất",
          serviceType: "Thủ tục hành chính công",
          provider: { "@type": "GovernmentOrganization", name: "GovFlow" },
        },
      ],
    },
  };

  return (
    <div className="min-h-screen">
      {/* JSON-LD structured data for search engines */}
      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {/* AI Hero Section */}
      <section className="relative py-20 px-4 text-center overflow-hidden">
        {/* Soft bg radial */}
        <div
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% 0%, oklch(0.65 0.15 280 / 0.15), transparent)",
          }}
        />

        {/* Tour button — top-right */}
        <div className="absolute right-4 top-4 z-10">
          <OnboardingTour tourId="citizen-portal" autoStart={true} />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-purple-200 bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700 mb-4">
            <Sparkles size={12} />
            Trợ lý AI Qwen3 · Hỗ trợ 24/7
          </div>

          <h1 className="text-4xl font-bold text-[var(--text-primary)] md:text-5xl">
            Cổng Dịch vụ công Thông minh
          </h1>
          <p className="mt-3 max-w-xl mx-auto text-lg text-[var(--text-secondary)]">
            Hỏi AI bằng ngôn ngữ thường để được hướng dẫn nhanh chóng
          </p>

          {/* AI search box */}
          <div className="max-w-2xl mx-auto mt-10" data-tour="portal-ai-search">
            {/* Hint banner */}
            <div className="mb-4 text-left">
              <HelpHintBanner id="portal-ai-search" variant="tip">
                Mô tả nhu cầu bằng tiếng Việt thường — AI sẽ gợi ý đúng thủ tục cho bạn.
              </HelpHintBanner>
            </div>
            <div className="relative">
              <textarea
                value={intentText}
                onChange={(e) => setIntentText(e.target.value)}
                onKeyDown={handleIntentKeyDown}
                placeholder="VD: Tôi muốn xin giấy phép xây nhà 3 tầng ở quận Cầu Giấy"
                rows={2}
                className="w-full resize-none rounded-2xl border-2 border-purple-200 bg-white px-6 py-5 text-base shadow-sm outline-none transition-colors placeholder:text-[var(--text-muted)] focus:border-purple-500 focus:ring-4 focus:ring-purple-100"
                aria-label="Mô tả yêu cầu hành chính"
              />
            </div>

            {/* Quick chips */}
            <div className="mt-3 flex flex-wrap justify-center gap-2">
              <QuickIntentChip
                label="Cấp phép xây dựng"
                onClick={() => handleChipClick("Tôi muốn xin cấp phép xây dựng")}
              />
              <QuickIntentChip
                label="Lý lịch tư pháp"
                onClick={() => handleChipClick("Tôi cần cấp phiếu lý lịch tư pháp")}
              />
              <QuickIntentChip
                label="Đăng ký kinh doanh"
                onClick={() => handleChipClick("Tôi muốn đăng ký thành lập doanh nghiệp")}
              />
              <QuickIntentChip
                label="GCN quyền sử dụng đất"
                onClick={() => handleChipClick("Tôi cần cấp giấy chứng nhận quyền sử dụng đất")}
              />
            </div>

            <button
              type="button"
              onClick={() => void handleAISearch()}
              disabled={intentMutation.isPending || !intentText.trim()}
              className="mt-5 inline-flex items-center gap-2 rounded-2xl px-8 py-3 text-base font-semibold text-white transition-all hover:opacity-90 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              style={{
                background: "var(--gradient-qwen)",
                boxShadow: "var(--shadow-qwen-glow)",
              }}
            >
              {intentMutation.isPending ? (
                <>
                  <span className="h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                  Đang phân tích...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Hỏi AI
                </>
              )}
            </button>
          </div>

          {/* Intent result card */}
          <AnimatePresence>
            {intentMutation.data && (
              <IntentResultCard
                intent={intentMutation.data}
                onSubmit={(code) => router.push(`/submit/${code}`)}
              />
            )}
          </AnimatePresence>
        </motion.div>
      </section>

      {/* Stats strip */}
      {stats && (
        <section
          className="border-y border-[var(--border-subtle)] bg-[var(--bg-surface)]"
          data-tour="portal-stats"
        >
          <div className="mx-auto max-w-5xl px-4 py-4">
            <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[var(--text-secondary)]">
              <span>
                Đã xử lý{" "}
                <span className="font-bold text-[var(--text-primary)]">
                  <AnimatedCounter value={stats.total_cases_processed} />
                </span>{" "}
                hồ sơ
              </span>
              <span className="text-[var(--border-default)]">·</span>
              <span>
                Trung bình{" "}
                <span className="font-bold text-[var(--text-primary)]">
                  <AnimatedCounter value={Math.round(stats.avg_processing_days)} />
                </span>{" "}
                ngày xử lý
              </span>
              <span className="text-[var(--border-default)]">·</span>
              <span>
                Tháng này:{" "}
                <span className="font-bold text-[var(--accent-success)]">
                  <AnimatedCounter value={stats.cases_this_month} />
                </span>{" "}
                hồ sơ
              </span>
            </div>
          </div>
        </section>
      )}

      {/* Life-event hero tiles */}
      <LifeEventTiles onNavigate={(code) => router.push(`/submit/${code}`)} />

      {/* Divider */}
      <div className="mx-auto max-w-5xl px-4 pt-8 pb-2">
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-[var(--border-subtle)]" />
          <span className="text-xs text-[var(--text-muted)]">Hoặc chọn thủ tục cụ thể</span>
          <div className="h-px flex-1 bg-[var(--border-subtle)]" />
        </div>
      </div>

      {/* 5 TTHC Cards */}
      <motion.section
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        data-tour="portal-tthc-cards"
        className="mx-auto grid max-w-5xl grid-cols-1 gap-4 px-4 py-12 sm:grid-cols-2 lg:grid-cols-3"
      >
        {TTHC_CARDS.map((tthc) => {
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
                <TTHCHoverCard tthc={tthc}>
                  <div className="flex cursor-default items-center gap-2 text-sm text-[var(--text-secondary)]">
                    <FolderOpen className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
                    <span>
                      Cần{" "}
                      <span className="font-medium text-[var(--text-primary)] underline decoration-dashed underline-offset-2">
                        {tthc.doc_count} thành phần hồ sơ
                      </span>
                    </span>
                  </div>
                </TTHCHoverCard>
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

      {/* Qwen AI Pitch — 3 slides for Build Day 2026 judges */}
      <QwenPitchSection />

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

          {/* Demo shortcut — skips manual submission for hackathon judges */}
          <div className="mt-4 flex items-center gap-3 rounded-md border border-dashed border-purple-300 bg-gradient-to-r from-purple-50 to-violet-50 px-4 py-3 dark:border-purple-700 dark:from-purple-950 dark:to-violet-950">
            <Sparkles size={16} className="shrink-0 text-purple-600 dark:text-purple-300" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-purple-900 dark:text-purple-100">
                Xem hồ sơ mẫu (demo)
              </p>
              <p className="text-xs text-purple-700 dark:text-purple-300">
                Hồ sơ CPXD đã xử lý sẵn — thấy đầy đủ trace, gap, citation.
              </p>
            </div>
            <button
              onClick={handleViewDemoCase}
              className="rounded-md border border-purple-400 bg-white px-3 py-1.5 text-xs font-medium text-purple-700 transition-colors hover:bg-purple-100 dark:border-purple-600 dark:bg-purple-900 dark:text-purple-100 dark:hover:bg-purple-800"
            >
              Xem HS-20260101-CASE0001 →
            </button>
          </div>
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
