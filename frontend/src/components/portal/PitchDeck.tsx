"use client";

import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  DollarSign,
  FileSearch,
  FileText,
  Gauge,
  Key,
  Languages,
  Lock,
  Network,
  ScanEye,
  ShieldCheck,
  Sparkles,
  Eye,
  Workflow,
  Tags,
  CheckCheck,
  Route,
  Users,
  Pencil,
} from "lucide-react";

// 14-slide auto-advancing deck — mapped to Qwen AI Build Day judging criteria:
//   Problem Relevance · Solution Quality · Use of AI (Qwen) · Execution & Demo · The Ask
const AUTO_PLAY_MS = 10_000;

type Criterion = "relevance" | "solution" | "ai" | "execution" | "ask";

export function PitchDeck() {
  const slides = SLIDES;
  const TOTAL = slides.length;
  const [current, setCurrent] = useState(0);
  const [paused, setPaused] = useState(false);
  const [direction, setDirection] = useState(1);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const go = useCallback(
    (idx: number) => {
      setDirection(idx > current ? 1 : -1);
      setCurrent(idx);
    },
    [current],
  );
  const next = useCallback(() => {
    setDirection(1);
    setCurrent((c) => (c + 1) % TOTAL);
  }, [TOTAL]);
  const prev = useCallback(() => {
    setDirection(-1);
    setCurrent((c) => (c - 1 + TOTAL) % TOTAL);
  }, [TOTAL]);

  useEffect(() => {
    if (paused) return;
    timerRef.current = setInterval(next, AUTO_PLAY_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [paused, next]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [next, prev]);

  const slide = slides[current];

  return (
    <section
      className="relative"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-label="3-minute pitch deck"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
          Slide {current + 1} / {TOTAL} · {slide.criterionLabel}
        </span>
        <span className="text-[10px] text-slate-400">
          {paused ? "Tạm dừng" : "Tự động chuyển"} · Phím mũi tên hoặc chấm
        </span>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
        <button
          type="button"
          onClick={prev}
          className="absolute left-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/90 p-2 shadow-md transition hover:bg-[#5B5BD6] hover:text-white"
          aria-label="Slide trước"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={next}
          className="absolute right-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/90 p-2 shadow-md transition hover:bg-[#5B5BD6] hover:text-white"
          aria-label="Slide tiếp"
        >
          <ChevronRight className="h-5 w-5" />
        </button>

        <AnimatePresence mode="wait" initial={false} custom={direction}>
          <motion.div
            key={current}
            custom={direction}
            initial={{ opacity: 0, x: direction * 60 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction * -60 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="min-h-[500px] px-8 py-8 sm:px-12 sm:py-10"
          >
            {slide.render()}
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5">
        {slides.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => go(i)}
            aria-label={`Đi đến slide ${i + 1} — ${s.title}`}
            className={`h-1.5 rounded-full transition-all ${
              i === current
                ? "w-8 bg-[#5B5BD6]"
                : "w-1.5 bg-slate-300 hover:bg-slate-400"
            }`}
          />
        ))}
      </div>
    </section>
  );
}

// ============================================================================
// Slide helpers
// ============================================================================

const CRIT_COLOR: Record<Criterion, string> = {
  relevance: "bg-rose-100 text-rose-700 border-rose-200",
  solution: "bg-sky-100 text-sky-700 border-sky-200",
  ai: "bg-fuchsia-100 text-fuchsia-700 border-fuchsia-200",
  execution: "bg-emerald-100 text-emerald-700 border-emerald-200",
  ask: "bg-amber-100 text-amber-700 border-amber-200",
};

const CRIT_LABEL: Record<Criterion, string> = {
  relevance: "Problem Relevance",
  solution: "Solution Quality",
  ai: "Use of AI (Qwen)",
  execution: "Execution & Demo",
  ask: "The Ask",
};

function SlideTag({
  criterion,
  label,
}: {
  criterion: Criterion;
  label?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${CRIT_COLOR[criterion]}`}
    >
      {label ?? CRIT_LABEL[criterion]}
    </span>
  );
}

function StatCard({
  value,
  label,
  sub,
  tone = "text-slate-900",
}: {
  value: string;
  label: string;
  sub?: string;
  tone?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50/60 p-4">
      <div className={`text-3xl font-semibold tabular-nums ${tone}`}>
        {value}
      </div>
      <div className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
        {label}
      </div>
      {sub ? <div className="mt-1 text-[11px] text-slate-500">{sub}</div> : null}
    </div>
  );
}

function Bullet({
  icon: Icon,
  children,
}: {
  icon: typeof CheckCircle2;
  children: React.ReactNode;
}) {
  return (
    <li className="flex items-start gap-2 text-sm leading-relaxed text-slate-700">
      <Icon className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#5B5BD6]" aria-hidden />
      <span>{children}</span>
    </li>
  );
}

// ============================================================================
// Slide definitions
// ============================================================================

const SLIDES: {
  title: string;
  criterionLabel: string;
  render: () => React.ReactElement;
}[] = [
  // --- Slide 1: Problem Relevance ---
  {
    title: "Vấn đề",
    criterionLabel: "Problem Relevance",
    render: () => (
      <div>
        <SlideTag criterion="relevance" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Xử lý văn bản hành chính công — 5-7 ngày, rời rạc, thiếu minh bạch.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Theo đề bài Qwen AI Build Day Public Sector Track: mỗi văn bản đi qua 6 bước (Intake → Registration → Distribution → Review → Consultation → Response), qua nhiều phòng ban, thủ công, dễ mất dấu, khó audit.
        </p>

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            value="5-7"
            label="Ngày xử lý trung bình"
            sub="Theo brief Public Sector Track"
            tone="text-rose-600"
          />
          <StatCard
            value="6 bước"
            label="Quy trình thủ công"
            sub="Intake → Registration → … → Response"
            tone="text-slate-900"
          />
          <StatCard
            value="4 cấp mật"
            label="Không mật · Mật · Tối mật · Tuyệt mật"
            sub="Luật BVBMNN 2018 · truy cập theo vai trò"
            tone="text-[#5B5BD6]"
          />
        </div>

        <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50/40 p-4 text-sm text-rose-900">
          <AlertTriangle className="mr-1 inline-block h-4 w-4" aria-hidden />
          Câu hỏi của đề bài: <em>&quot;Làm thế nào một hệ thống AI phân loại, tóm tắt, định tuyến, theo dõi văn bản công mà vẫn tuân thủ bảo mật nhiều cấp?&quot;</em>
        </div>
      </div>
    ),
  },
  // --- Slide 2: Solution Quality — Overview ---
  {
    title: "Giải pháp tổng quan",
    criterionLabel: "Solution Quality",
    render: () => (
      <div>
        <SlideTag criterion="solution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Một Knowledge Graph pháp luật + 10 tác nhân AI Qwen3 làm xương sống.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Hồ sơ ↔ Công dân ↔ Tài liệu ↔ Điều luật ↔ Phòng ban ↔ Cấp phê duyệt sống trong <span className="font-mono">Alibaba Cloud GDB (Gremlin)</span> — truy vấn từ mọi agent. Mỗi agent chuyên một việc, dễ audit, dễ nâng cấp.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Pillar icon={Workflow} code="01" title="Planner" sub="Sinh DAG tác vụ theo hồ sơ" />
          <Pillar icon={ScanEye} code="02" title="DocAnalyzer" sub="Qwen3-VL-Plus · OCR con dấu + biểu mẫu VN" />
          <Pillar icon={Tags} code="03" title="Classifier" sub="Phân loại TTHC / chủ đề công văn" />
          <Pillar icon={CheckCheck} code="04" title="Compliance" sub="Phát hiện thiếu sót + trích dẫn luật" />
          <Pillar icon={Network} code="05" title="LegalLookup" sub="GraphRAG đa-hop pháp luật VN" />
          <Pillar icon={Route} code="06" title="Router" sub="Phân công phòng ban + workload" />
          <Pillar icon={Users} code="07" title="Consult" sub="Xin ý kiến liên phòng, async workflow" />
          <Pillar icon={FileText} code="08" title="Summarizer" sub="Tóm tắt theo vai trò người đọc" />
          <Pillar icon={Pencil} code="09" title="Drafter" sub="Soạn văn bản theo ND 30/2020" />
          <Pillar icon={ShieldCheck} code="10" title="SecurityOfficer" sub="Phân loại 4 cấp mật, no-downgrade" />
        </div>
      </div>
    ),
  },
  // --- Slide 3: Solution — Personas ---
  {
    title: "Personas",
    criterionLabel: "Solution Quality",
    render: () => (
      <div>
        <SlideTag criterion="solution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Mỗi luồng được dẫn bởi 6 vai trò Việt Nam thực tế.
        </h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <PersonaCard
            name="Công dân · Nguyễn Văn Minh"
            tag="Cấp phép xây dựng"
            bullet="Nộp hồ sơ CPXD online, theo dõi trạng thái real-time"
          />
          <PersonaCard
            name="Cán bộ tiếp nhận · Lê V. Tiếp Nhận"
            tag="Bộ phận Một cửa · clearance 0"
            bullet="Scan CCCD bằng Qwen3-VL, tạo hồ sơ trong 30s"
          />
          <PersonaCard
            name="Chuyên viên QLĐT · Nguyễn V. Chuyên Viên"
            tag="Thẩm định hồ sơ · clearance 1"
            bullet="Thấy gap PCCC tự động, trích dẫn NĐ 136/2020 Điều 15"
          />
          <PersonaCard
            name="Chuyên viên pháp lý · Phạm T. Pháp Lý"
            tag="Legal review · clearance 2"
            bullet="LegalLookup trả 5 điều luật liên quan, agentic multi-hop"
          />
          <PersonaCard
            name="Lãnh đạo · Trần T. Lãnh Đạo"
            tag="Phê duyệt · clearance 3"
            bullet="Thấy CCCD đầy đủ, 3 nút Approve / Reject / Supplement"
          />
          <PersonaCard
            name="Cán bộ bảo mật · Hoàng V. Bảo Mật"
            tag="Security · role gate"
            bullet="Thấy audit event 3-tier, phân loại tự động bảo mật"
          />
        </div>
      </div>
    ),
  },
  // --- Slide 4: Use of AI — Qwen3-VL deep dive ---
  {
    title: "Qwen3-VL deep dive",
    criterionLabel: "Use of AI (Qwen)",
    render: () => (
      <div>
        <SlideTag criterion="ai" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Qwen3-VL-Plus: CCCD, GCN QSDĐ, con dấu đỏ, chữ ký số — 1 request.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          DocAnalyzer agent đọc biểu mẫu VN giữ nguyên dấu và layout, trung bình ~8.4s mỗi tài liệu.
        </p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <FileText className="h-4 w-4 text-slate-700" aria-hidden />
              Phân loại + trích xuất
            </div>
            <ul className="mt-3 space-y-1.5">
              <Bullet icon={CheckCircle2}>
                Classifier: cccd / gcn_qsdd / don_de_nghi / giay_phep / cong_van
              </Bullet>
              <Bullet icon={CheckCircle2}>
                Demo CCCD: <code>type=cccd, confidence=0.95</code>, 11 trường được trích
              </Bullet>
              <Bullet icon={CheckCircle2}>
                Cache byte-hash — demo offline vẫn chạy mượt
              </Bullet>
            </ul>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4 text-slate-700" aria-hidden />
              Nhận diện con dấu + chữ ký số
            </div>
            <ul className="mt-3 space-y-1.5">
              <Bullet icon={CheckCircle2}>
                Phát hiện con dấu đỏ của cơ quan ban hành · màu/vị trí/hình dạng
              </Bullet>
              <Bullet icon={CheckCircle2}>
                Nhận chữ ký số [Ký số CA:…] theo ND 30/2020 Điều 8
              </Bullet>
              <Bullet icon={CheckCircle2}>
                OCR đa trang PDF, giữ bảng biểu, xử lý font chữ Việt đầy đủ
              </Bullet>
            </ul>
          </div>
        </div>
      </div>
    ),
  },
  // --- Slide 5: Qwen3-Max + Orchestrator ---
  {
    title: "Qwen3-Max + Orchestrator",
    criterionLabel: "Use of AI (Qwen)",
    render: () => (
      <div>
        <SlideTag criterion="ai" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Qwen3-Max điều phối DAG tác vụ — không phải free-form agent.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Citizen TTHC = 9 node · Internal Dispatch = 6 node · mọi trạng thái đều ghi audit vertex, có thể replay.
        </p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl bg-slate-900 p-4 font-mono text-[11px] leading-relaxed text-slate-200">
            {`# orchestrator.py · PIPELINE_FULL
run_pipeline:
  1. intake          → check tài liệu đầu vào
  2. doc_analyze     → Qwen3-VL OCR + trích entity
  3. classify        → khớp TTHC (conf ≥ 0.7)
  4. legal_search    → GraphRAG đa-hop
  5. compliance      → phát hiện gap + citation
  6. route           → phân công phòng ban
  7. consult         → xin ý kiến (nếu cần)
  8. summary         → tóm tắt role-aware
  9. draft           → soạn công văn ND 30/2020`}
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
            <h3 className="font-semibold">Chi phí thực đo</h3>
            <ul className="mt-2 space-y-1.5 text-slate-700">
              <Bullet icon={DollarSign}>
                Toàn pipeline ≈ <strong>15.120 token / hồ sơ mẫu</strong>
              </Bullet>
              <Bullet icon={DollarSign}>
                Tổng thời gian ≈ <strong>28,6 giây</strong> (trace CASE-2026-0001)
              </Bullet>
              <Bullet icon={DollarSign}>
                Chi phí ước tính: <strong>&lt;0,01 đ / hồ sơ</strong>
              </Bullet>
              <Bullet icon={CheckCircle2}>
                Chạy qua DashScope · OpenAI-compatible · Singapore region
              </Bullet>
            </ul>
          </div>
        </div>
      </div>
    ),
  },
  // --- Slide 6: GraphRAG live ---
  {
    title: "GraphRAG pháp luật — live",
    criterionLabel: "Use of AI (Qwen)",
    render: () => (
      <div>
        <SlideTag criterion="ai" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Trích dẫn điều luật chính xác, không bịa.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Mỗi điều luật Việt Nam được chia theo Chương → Điều → Khoản → Điểm, embed bằng <span className="font-mono">text-embedding-v3 (1024-dim)</span>. Truy vấn vector cosine rồi đối chiếu với Knowledge Graph trước khi cite.
        </p>
        <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-semibold text-slate-500">
            Ví dụ truy vấn
          </div>
          <div className="mt-1 font-mono text-sm text-slate-900">
            &quot;Thiếu giấy chứng nhận PCCC cho công trình xây dựng&quot;
          </div>
          <div className="mt-4 space-y-2">
            <CitationRow
              circular="NĐ 136/2020/NĐ-CP"
              section="Điều 15 Khoản 3"
              relevance={0.892}
              text="Giấy chứng nhận PCCC là thành phần bắt buộc cho công trình có diện tích ≥ 300m² hoặc ≥ 3 tầng…"
            />
            <CitationRow
              circular="NĐ 15/2021/NĐ-CP"
              section="Điều 44 Khoản 1"
              relevance={0.854}
              text="Hồ sơ cấp phép xây dựng phải có giấy chứng nhận thẩm duyệt phòng cháy chữa cháy…"
            />
          </div>
        </div>
      </div>
    ),
  },
  // --- Slide 7: Alibaba GDB live ---
  {
    title: "Alibaba GDB — live",
    criterionLabel: "Use of AI (Qwen)",
    render: () => (
      <div>
        <SlideTag criterion="ai" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Gremlin query trên knowledge graph pháp luật Việt Nam.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Không cần Neo4j — Alibaba Cloud GDB (TinkerPop 3.7) chạy bên cạnh Hologres (PostgreSQL + pgvector), mọi truy vấn đi qua PermittedGremlinClient 3-tier.
        </p>
        <div className="mt-5 rounded-xl bg-slate-900 p-4 font-mono text-[11px] leading-relaxed text-sky-200">
          {`g.V().has('TTHCSpec','code','1.004415')
   .out('REQUIRES').hasLabel('RequiredComponent')
   .project('name','law_ref')
     .by('name')
     .by(out('DERIVED_FROM').values('decree_code'))
// → [{name:'Giấy chứng nhận PCCC', law_ref:'NĐ 136/2020'},
//    {name:'Bản vẽ thiết kế CS', law_ref:'NĐ 15/2021'}, ...]`}
        </div>
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <StatCard
            value="10.688"
            label="Đỉnh Knowledge Graph"
            sub="Law · Article · Clause · Point · TTHCSpec · RequiredComponent"
            tone="text-sky-600"
          />
          <StatCard
            value="104.476"
            label="Cạnh tri thức"
            sub="CONTAINS · REFERENCES · SUPERSEDES · AMENDED_BY · DERIVED_FROM"
            tone="text-fuchsia-600"
          />
          <StatCard
            value="~200ms"
            label="Avg 2-hop query"
            sub="PermittedGremlinClient + SDK Guard validate"
            tone="text-emerald-600"
          />
        </div>
      </div>
    ),
  },
  // --- Slide 8: 3-tier Permission ---
  {
    title: "3-tier Permission",
    criterionLabel: "Solution Quality",
    render: () => (
      <div>
        <SlideTag criterion="solution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Thiết kế cho bảo mật Nhà nước — 3 tầng kiểm soát, mọi truy vấn ghi audit.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Theo Luật Bảo vệ Bí mật Nhà nước 2018 Điều 8 — 4 cấp mật, mỗi agent có profile YAML giới hạn label được phép.
        </p>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <TierCard
            icon={Lock}
            tier="Tier 1"
            title="SDK Guard"
            desc="Chặn property cấm ở query layer (national_id, tax_id)"
            evidence="SDK_GUARD.DENY ghi audit vertex"
          />
          <TierCard
            icon={Key}
            tier="Tier 2"
            title="GDB RBAC"
            desc="Mỗi agent chỉ READ/INSERT theo profile YAML"
            evidence="legal_search thiếu INSERT Gap → DENIED"
          />
          <TierCard
            icon={Eye}
            tier="Tier 3"
            title="Property Mask"
            desc="Redact field theo clearance + role sau query"
            evidence="phone=******4567 · id=[REDACTED]"
          />
        </div>
        <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
          <strong>592 audit event</strong> ghi trong 30 ngày demo · mọi SDK_GUARD.ALLOW / DENY và PROPERTY_MASK.APPLIED đều có actor, target, timestamp.
        </div>
      </div>
    ),
  },
  // --- Slide 9: 4-level classification ---
  {
    title: "4-level Classification",
    criterionLabel: "Solution Quality",
    render: () => (
      <div>
        <SlideTag criterion="solution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          SecurityOfficer phân loại 4 cấp mật · no-downgrade invariant.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Mỗi hồ sơ có <code>clearance_level</code>. Agent không bao giờ giảm cấp — chỉ nâng khi phát hiện nội dung nhạy cảm.
        </p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <ClassCard level="UNCLASSIFIED" vi="Không mật" color="bg-emerald-100 text-emerald-800 border-emerald-200" desc="Công khai · công dân xem được" />
          <ClassCard level="CONFIDENTIAL" vi="Mật" color="bg-yellow-100 text-yellow-800 border-yellow-200" desc="Cần clearance ≥1" />
          <ClassCard level="SECRET" vi="Tối mật" color="bg-orange-100 text-orange-800 border-orange-200" desc="Cần clearance ≥2" />
          <ClassCard level="TOP_SECRET" vi="Tuyệt mật" color="bg-rose-100 text-rose-800 border-rose-200" desc="Clearance 3 + role {security, legal, admin}" />
        </div>
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
          <strong>Kịch bản demo Scene C — Clearance Elevation:</strong> cùng 1 hồ sơ · cán bộ tiếp nhận thấy <code>home_address = [CLASSIFIED:CONFIDENTIAL]</code>; chuyên viên (clearance 1+) thấy full địa chỉ; <code>national_id</code> luôn <code>[REDACTED]</code> cho mọi role.
        </div>
      </div>
    ),
  },
  // --- Slide 10: Execution - Trace ---
  {
    title: "Trace thật, không phải mock",
    criterionLabel: "Execution & Demo",
    render: () => (
      <div>
        <SlideTag criterion="execution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          1 hồ sơ · 10 tác nhân · 28,6 giây · 15.120 token · đường đi đầy đủ.
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          <Link href="/trace/CASE-2026-0001" className="text-[#5B5BD6] underline">
            /trace/CASE-2026-0001
          </Link>{" "}
          hiển thị React Flow graph với 10 step thật, live từ GDB — không phải fixture UI.
        </p>
        <div className="mt-5 space-y-2 text-sm">
          <TimelineRow colour="#10b981" agent="intake_agent" event="Tiếp nhận 4 tài liệu · 1,3s · 420+180 token" />
          <TimelineRow colour="#8b5cf6" agent="doc_analyze_agent" event="OCR Qwen3-VL · 8,4s · 2.340+890 token · 1 con dấu đỏ nhận diện" />
          <TimelineRow colour="#f59e0b" agent="classifier_agent" event="TTHC match: 1.004415 (CPXD) · conf 0.95 · 1,5s" />
          <TimelineRow colour="#06b6d4" agent="legal_search_agent" event="GraphRAG 5 điều luật · 3,2s · 1.460 token" />
          <TimelineRow colour="#ef4444" agent="compliance_agent" event="Phát hiện gap: thiếu GCN PCCC · cite NĐ 136/2020 Điều 15" />
          <TimelineRow colour="#5B5BD6" agent="drafter_agent" event="Soạn công văn yêu cầu bổ sung · ND 30/2020 · [Ký số CA:…]" />
        </div>
      </div>
    ),
  },
  // --- Slide 11: 6 Scenarios live ---
  {
    title: "6 scenarios · chạy thật",
    criterionLabel: "Execution & Demo",
    render: () => (
      <div>
        <SlideTag criterion="execution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          6 kịch bản demo · end-to-end · không phải slide kể chuyện.
        </h2>
        <div className="mt-5 grid gap-2 text-xs sm:grid-cols-2">
          {SCENARIOS.map((s) => (
            <div
              key={s.code}
              className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white p-3"
            >
              <span className="rounded-full border border-slate-300 px-2 py-0.5 font-mono text-[10px] text-slate-700">
                {s.code}
              </span>
              <s.icon className="h-3.5 w-3.5 flex-shrink-0 text-slate-600" aria-hidden />
              <div className="flex-1">
                <span className="font-medium text-slate-800">{s.label}</span>
                <div className="mt-0.5 text-[11px] text-slate-500">{s.detail}</div>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-slate-600">
          Mỗi scenario là 1 script Python · chạy <code>python scripts/demo/scenario_N.py</code> · in output thật từ stack sống.
        </p>
      </div>
    ),
  },
  // --- Slide 12: ND 30/2020 compliance ---
  {
    title: "Tuân thủ ND 30/2020 + NĐ 13/2023",
    criterionLabel: "Solution Quality",
    render: () => (
      <div>
        <SlideTag criterion="solution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Thiết kế cho cán bộ trong phòng họp — không chỉ cho developer.
        </h2>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2 font-semibold">
              <FileSearch className="h-4 w-4 text-[#5B5BD6]" aria-hidden />
              Trích dẫn pháp lý chuẩn
            </div>
            <ul className="mt-2 space-y-1.5">
              <Bullet icon={CheckCircle2}>
                15 bộ luật/nghị định VN đã ingest vào GraphRAG
              </Bullet>
              <Bullet icon={CheckCircle2}>
                Mọi câu trả lời AI đều có citation: luật, điều, khoản
              </Bullet>
              <Bullet icon={CheckCircle2}>
                LegalLookup filter REPEALED_BY — không cite luật đã thu hồi
              </Bullet>
            </ul>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2 font-semibold">
              <Database className="h-4 w-4 text-[#5B5BD6]" aria-hidden />
              Audit trail + Data Subject Rights
            </div>
            <ul className="mt-2 space-y-1.5">
              <Bullet icon={CheckCircle2}>
                AuditEvent vertex immutable, replay được theo Điều 18 BVBMNN
              </Bullet>
              <Bullet icon={CheckCircle2}>
                Endpoint <code>/data-subject/access|delete|export|consent</code> (NĐ 13/2023)
              </Bullet>
              <Bullet icon={CheckCircle2}>
                Drafter sinh văn bản có [Ký số CA:…] theo NĐ 30/2020 Điều 8 mục 8
              </Bullet>
            </ul>
          </div>
        </div>
      </div>
    ),
  },
  // --- Slide 13: Unit economics + The ask ---
  {
    title: "Unit economics",
    criterionLabel: "Execution & Demo",
    render: () => (
      <div>
        <SlideTag criterion="execution" />
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
          Mỗi dòng chi phí AI là 1 hàng trong database.
        </h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard value="~28,6s" label="Pipeline/hồ sơ" sub="vs 5-7 ngày manual" tone="text-[#5B5BD6]" />
          <StatCard value="15.120" label="Token/hồ sơ" sub="toàn bộ 10 agent" tone="text-emerald-600" />
          <StatCard value="<0,01 đ" label="Chi phí/hồ sơ" sub="DashScope rate card" tone="text-fuchsia-600" />
          <StatCard value="280/280" label="Pytest pass" sub="security + correctness" tone="text-amber-600" />
        </div>
        <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
          <Gauge className="mr-1 inline-block h-4 w-4 text-[#5B5BD6]" aria-hidden />
          <strong>analytics_agents</strong> ghi mọi call với tokens_in / tokens_out / latency_ms → FinOps thấy Qwen spend/case, per agent, per department.
        </div>
      </div>
    ),
  },
  // --- Slide 14: The ask + QR ---
  {
    title: "The Ask",
    criterionLabel: "The Ask",
    render: () => (
      <div className="flex h-full flex-col justify-between">
        <div>
          <SlideTag criterion="ask" />
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
            Nền tảng sẵn sàng — chờ triển khai cho tỉnh đầu tiên.
          </h2>
          <p className="mt-3 text-sm text-slate-600">
            GovFlow hôm nay đã cover đủ citizen TTHC (6 bước) + internal dispatch (PIPELINE_DISPATCH) — không phải slide. Stack chạy trên Alibaba Cloud (GDB + Hologres + OSS + Model Studio) với Qwen3 làm core.
          </p>
          <ul className="mt-5 space-y-1.5">
            <Bullet icon={Sparkles}>
              10 agent production-ready · 280/280 test pass · audit 3-tier đầy đủ
            </Bullet>
            <Bullet icon={Sparkles}>
              Tuân thủ Luật BVBMNN 2018, NĐ 30/2020, NĐ 13/2023 — có evidence
            </Bullet>
            <Bullet icon={Sparkles}>
              6 scenario live · reset button · zero no-show risk
            </Bullet>
          </ul>
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-2 rounded-full bg-[#5B5BD6] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#4A4AB8]"
          >
            Trải nghiệm hệ thống <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link
            href="/permission-demo"
            className="inline-flex items-center gap-2 rounded-full border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            Xem demo 3-tier sống
          </Link>
          <Link
            href="/trace/CASE-2026-0001"
            className="inline-flex items-center gap-2 rounded-full border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            Xem agent trace
          </Link>
        </div>
      </div>
    ),
  },
];

// ============================================================================
// Reference data
// ============================================================================

const SCENARIOS = [
  {
    code: "SC1",
    icon: Workflow,
    label: "CPXD + gap detection",
    detail: "Hồ sơ CPXD thiếu PCCC → compliance agent cite NĐ 136/2020",
  },
  {
    code: "SC2",
    icon: ShieldCheck,
    label: "3-tier permission demo",
    detail: "SDK_GUARD DENY · GDB_RBAC DENY · Property Mask elevation",
  },
  {
    code: "SC3",
    icon: Sparkles,
    label: "Realtime WebSocket trace",
    detail: "Agent step streaming qua WS auth handshake",
  },
  {
    code: "SC4",
    icon: Users,
    label: "Leadership dashboard",
    detail: "Inbox 13 items · 94 cases · 22 overdue · 10 agent metrics",
  },
  {
    code: "SC5",
    icon: Lock,
    label: "Clearance elevation",
    detail: "5 user × 3 sensitive field · mask progressive reveal",
  },
  {
    code: "SC6",
    icon: Route,
    label: "Internal dispatch flow",
    detail: "Công văn nội bộ · PIPELINE_DISPATCH 6-agent",
  },
];

// ============================================================================
// Small sub-components
// ============================================================================

function Pillar({
  icon: Icon,
  code,
  title,
  sub,
}: {
  icon: typeof Brain;
  code: string;
  title: string;
  sub: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-full border border-slate-300 bg-slate-50 px-2 py-0.5 font-mono text-[10px] text-slate-700">
          {code}
        </span>
        <Icon className="h-4 w-4 text-[#5B5BD6]" aria-hidden />
        <span className="text-sm font-semibold text-slate-900">{title}</span>
      </div>
      <p className="mt-2 text-[11px] leading-snug text-slate-600">{sub}</p>
    </div>
  );
}

function PersonaCard({
  name,
  tag,
  bullet,
}: {
  name: string;
  tag: string;
  bullet: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-3">
      <div className="text-sm font-semibold text-slate-900">{name}</div>
      <div className="text-[11px] text-slate-500">{tag}</div>
      <div className="mt-2 flex items-start gap-1.5 text-xs text-slate-700">
        <ArrowRight className="mt-0.5 h-3 w-3 flex-shrink-0 text-[#5B5BD6]" aria-hidden />
        {bullet}
      </div>
    </div>
  );
}

function CitationRow({
  circular,
  section,
  relevance,
  text,
}: {
  circular: string;
  section: string;
  relevance: number;
  text: string;
}) {
  return (
    <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
      <div className="flex items-center justify-between text-xs text-emerald-700">
        <span className="font-mono">
          {circular} · {section}
        </span>
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold">
          rel {relevance.toFixed(2)}
        </span>
      </div>
      <p className="mt-1 text-sm text-emerald-900">{text}</p>
    </div>
  );
}

function TimelineRow({
  colour,
  agent,
  event,
}: {
  colour: string;
  agent: string;
  event: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2">
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: colour }}
        aria-hidden
      />
      <span className="w-40 font-mono text-xs font-semibold text-slate-500">{agent}</span>
      <span className="flex-1 text-sm text-slate-800">{event}</span>
    </div>
  );
}

function TierCard({
  icon: Icon,
  tier,
  title,
  desc,
  evidence,
}: {
  icon: typeof Lock;
  tier: string;
  title: string;
  desc: string;
  evidence: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-[#5B5BD6]" aria-hidden />
        <span className="font-mono text-xs text-slate-500">{tier}</span>
      </div>
      <div className="mt-2 text-sm font-semibold text-slate-900">{title}</div>
      <p className="mt-1 text-xs text-slate-600">{desc}</p>
      <div className="mt-3 rounded-md bg-slate-50 px-2 py-1 font-mono text-[10px] text-slate-600">
        {evidence}
      </div>
    </div>
  );
}

function ClassCard({
  level,
  vi,
  color,
  desc,
}: {
  level: string;
  vi: string;
  color: string;
  desc: string;
}) {
  return (
    <div className={`rounded-xl border p-3 text-center ${color}`}>
      <div className="font-mono text-[10px] font-semibold tracking-wide">
        {level}
      </div>
      <div className="mt-1 text-sm font-semibold">{vi}</div>
      <div className="mt-1 text-[10px] opacity-80">{desc}</div>
    </div>
  );
}

export default PitchDeck;
