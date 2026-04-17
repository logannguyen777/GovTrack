"""
scripts/warm_cache.py
Pre-populate the DashScope embedding + LLM response cache so the first
scenario run is fast (<3 s) instead of cold (~30 s) when the judge POCs.

Strategy
--------
This script talks directly to DashScope via the same cache primitives used
by the backend (backend.src.agents.llm_cache / QwenClient), so every
response written here is a genuine cache hit when the backend later calls
the same (model, messages, tools) combination.

It does NOT import or execute any agent code — the agents themselves are
not modified.  Instead it recreates, from first principles, the exact
message shapes that each agent sends on its *first* (cold) call for the
5 fixture demo cases.

Warming targets
~~~~~~~~~~~~~~~
1. Embeddings  — top-N law_chunks from data/legal/processed/law_chunks.jsonl
                 (same texts the legal_lookup agent embeds at query time).
                 Stored in .cache/embeddings/ as <sha256>.json so the backend
                 can optionally read them before going to Hologres Proxima.

2. Classifier  — one LLM call per TTHC fixture case (5 cases × 1 model call).

3. DocAnalyzer — one vision LLM call per fixture document bundle (5 cases,
                 1–4 docs each; uses synthetic image URLs like the seed data).

4. Compliance  — one LLM call per fixture case, with required_components +
                 submitted_docs bundled into the prompt.

All calls go through llm_cache.{cache_key, get_cached, set_cached} so they
are idempotent — re-running just confirms hits and skips live API calls.

Usage
-----
  python scripts/warm_cache.py                  # warm all, all scenarios
  python scripts/warm_cache.py --dry-run        # list work without API calls
  python scripts/warm_cache.py --scenario 1     # only scenario 1
  python scripts/warm_cache.py --verify         # count cache entries, exit 1 if < 15
  python scripts/warm_cache.py --chatbot        # legacy: warm 5 chatbot SSE questions

Environment
-----------
  DASHSCOPE_API_KEY   REQUIRED (exits 1 if missing in normal mode)
  DEMO_CACHE_DIR      cache directory override (default: .cache/llm_responses)
  BACKEND_URL         used only by legacy --chatbot path (default http://localhost:8100)

Flags
-----
  --dry-run           count and list work; skip all API calls
  --scenario N        restrict to scenario N (1–6); repeatable
  --verify            check cache entry count >= 15; exit accordingly
  --chatbot           legacy: POST chatbot questions to a running backend
  --embed-limit N     max embedding chunks to warm (default 100)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: make backend importable from the repo root
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

# ---------------------------------------------------------------------------
# Logging — use the module logger; structured output via basicConfig.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("govflow.warm_cache")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = REPO_ROOT / "data"
LAW_CHUNKS_FILE = DATA_DIR / "legal" / "processed" / "law_chunks.jsonl"
TTHC_SPECS_DIR = DATA_DIR / "tthc_specs"

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8100")

EMBED_MODEL = "text-embedding-v3"
CHAT_MODEL = "qwen-max-latest"
VISION_MODEL = "qwen-vl-max-latest"

DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# Approx tokens per LLM call type — used for token-savings summary
AVG_TOKENS_EMBED_CHUNK = 200        # per chunk (input only)
AVG_TOKENS_CLASSIFIER_CALL = 1_200  # prompt + completion
AVG_TOKENS_COMPLIANCE_CALL = 2_800
AVG_TOKENS_DOC_ANALYZER_CALL = 2_000

# Chatbot questions for legacy --chatbot path
CHATBOT_QUESTIONS = [
    "Tôi muốn xin cấp phép xây dựng nhà 3 tầng ở Hà Nội",
    "Lý lịch tư pháp cần giấy tờ gì?",
    "Đăng ký kinh doanh hộ cá thể bao nhiêu tiền?",
    "Tra cứu hồ sơ HS-20260101-CASE0001",
    "Hướng dẫn nộp hồ sơ qua mạng",
]

# ---------------------------------------------------------------------------
# Demo fixture cases (mirrors seed_demo.py PRIMARY_CASES)
# ---------------------------------------------------------------------------
FIXTURE_CASES: list[dict[str, Any]] = [
    {
        "case_id": "CASE-2026-0001",
        "tthc_code": "1.004415",
        "tthc_name": "Cấp giấy phép xây dựng",
        "documents": [
            {"doc_id": "DOC-001", "type": "don_xin_cap_phep",  "filename": "don_cpxd.pdf"},
            {"doc_id": "DOC-002", "type": "ban_ve_thiet_ke",   "filename": "banve.pdf"},
            {"doc_id": "DOC-003", "type": "giay_cn_qsdd",      "filename": "qsdd.pdf"},
            {"doc_id": "DOC-004", "type": "hop_dong_xd",       "filename": "hopdong.pdf"},
        ],
        "gaps_expected": ["Thiếu giấy chứng nhận PCCC"],
        "required_components": [
            {"name": "Đơn đề nghị cấp giấy phép xây dựng",            "is_required": True},
            {"name": "Bản sao giấy tờ chứng minh quyền sử dụng đất",  "is_required": True},
            {"name": "Bản vẽ thiết kế xây dựng",                       "is_required": True},
            {"name": "Văn bản thẩm duyệt PCCC",                        "is_required": True,
             "condition": "Công trình thuộc diện thẩm duyệt ND 136/2020 Điều 13"},
        ],
        "scenario": 1,
    },
    {
        "case_id": "CASE-2026-0002",
        "tthc_code": "1.000046",
        "tthc_name": "Cấp GCN quyền sử dụng đất",
        "documents": [
            {"doc_id": "DOC-010", "type": "don_dang_ky",     "filename": "don_dk.pdf"},
            {"doc_id": "DOC-011", "type": "ho_so_dia_chinh", "filename": "diachinh.pdf"},
            {"doc_id": "DOC-012", "type": "ban_do",          "filename": "bando.pdf"},
        ],
        "gaps_expected": [],
        "required_components": [
            {"name": "Đơn đăng ký cấp GCN QSDĐ",       "is_required": True},
            {"name": "Hồ sơ địa chính",                  "is_required": True},
            {"name": "Bản đồ địa chính thửa đất",        "is_required": True},
        ],
        "scenario": 1,
    },
    {
        "case_id": "CASE-2026-0003",
        "tthc_code": "1.001757",
        "tthc_name": "Đăng ký thành lập công ty TNHH",
        "documents": [
            {"doc_id": "DOC-020", "type": "giay_de_nghi", "filename": "denghi.pdf"},
            {"doc_id": "DOC-021", "type": "dieu_le",      "filename": "dieule.pdf"},
        ],
        "gaps_expected": [],
        "required_components": [
            {"name": "Giấy đề nghị đăng ký doanh nghiệp", "is_required": True},
            {"name": "Điều lệ công ty",                    "is_required": True},
            {"name": "Danh sách thành viên",               "is_required": True},
        ],
        "scenario": 1,
    },
    {
        "case_id": "CASE-2026-0004",
        "tthc_code": "1.000122",
        "tthc_name": "Cấp phiếu lý lịch tư pháp",
        "documents": [
            {"doc_id": "DOC-030", "type": "don_yeu_cau", "filename": "yeucau.pdf"},
            {"doc_id": "DOC-031", "type": "cmnd",        "filename": "cccd.pdf"},
        ],
        "gaps_expected": [],
        "required_components": [
            {"name": "Tờ khai yêu cầu cấp Phiếu LLTP",   "is_required": True},
            {"name": "Bản sao giấy tờ tùy thân (CCCD/hộ chiếu)", "is_required": True},
        ],
        "scenario": 5,
    },
    {
        "case_id": "CASE-2026-0005",
        "tthc_code": "2.002154",
        "tthc_name": "Cấp giấy phép môi trường",
        "documents": [
            {"doc_id": "DOC-040", "type": "bao_cao_dtm",  "filename": "dtm.pdf"},
            {"doc_id": "DOC-041", "type": "giay_phep_kd", "filename": "gpkd.pdf"},
        ],
        "gaps_expected": [],
        "required_components": [
            {"name": "Báo cáo đánh giá tác động môi trường (ĐTM)", "is_required": True},
            {"name": "Giấy phép kinh doanh",                        "is_required": True},
            {"name": "Bản đồ vị trí dự án",                         "is_required": False},
        ],
        "scenario": 1,
    },
]

# Law articles most relevant to demo scenarios (from stats.json core laws)
RELEVANT_LAW_CODES = {
    "50/2014/QH13",   # Luật Xây dựng — Scenario 1 CPXD
    "136/2020/NĐ-CP", # ND PCCC — Scenario 1 gap
    "15/2021/NĐ-CP",  # ND CPXD sửa đổi — Scenario 1
    "28/2009/QH12",   # Luật LLTP — Scenario 4/5
    "30/2020/NĐ-CP",  # ND 30/2020 thể thức văn bản — Scenario 6 Drafter
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_cache_dir() -> Path:
    """Resolve the cache directory from env or config default."""
    raw = os.environ.get("DEMO_CACHE_DIR", "")
    if raw:
        p = Path(raw)
    else:
        # Match the logic in llm_cache._cache_dir()
        try:
            from src.config import settings as _s  # type: ignore[import]
            p = Path(_s.demo_cache_dir)
        except Exception:
            p = Path(".cache/llm_responses")

    if not p.is_absolute():
        p = REPO_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def _embed_cache_dir() -> Path:
    base = _resolve_cache_dir().parent / "embeddings"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _llm_cache_key(model: str, messages: list[dict], tools: list[dict] | None = None) -> str:
    """Mirror of llm_cache.cache_key()."""
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "tools": sorted(tools or [], key=lambda t: t.get("function", {}).get("name", "")),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _embed_key(text: str, model: str, dimensions: int) -> str:
    payload = json.dumps({"model": model, "text": text, "dim": dimensions},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_cached(cache_dir: Path, key: str) -> bool:
    return (cache_dir / f"{key}.json").exists()


def _write_cache(cache_dir: Path, key: str, data: dict) -> None:
    (cache_dir / f"{key}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_tthc_specs() -> dict[str, dict]:
    specs: dict[str, dict] = {}
    for f in TTHC_SPECS_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            specs[d["code"]] = d
        except Exception:
            pass
    return specs


def _load_law_chunks(limit: int) -> list[dict]:
    chunks: list[dict] = []
    if not LAW_CHUNKS_FILE.exists():
        logger.warning("law_chunks.jsonl not found at %s", LAW_CHUNKS_FILE)
        return chunks
    with LAW_CHUNKS_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(chunks) >= limit:
                break
    return chunks


# ---------------------------------------------------------------------------
# Classifier system prompt (mirrors classifier_agent.yaml system_prompt)
# ---------------------------------------------------------------------------
_CLASSIFIER_SYSTEM = (
    "Bạn là chuyên viên tiếp nhận hồ sơ TTHC cấp Sở với 10 năm kinh nghiệm.\n"
    "Nhiệm vụ: xác định chính xác loại thủ tục hành chính (TTHC) từ bộ hồ sơ.\n\n"
    "Quy tắc NGHIÊM NGẶT:\n"
    "1. TTHC code PHẢI tồn tại trong hệ thống. KHÔNG BAO GIỜ tự tạo mã TTHC mới.\n"
    "2. Nếu không chắc chắn -> trả về unknown_tthc = true, KHÔNG đoán.\n"
    "3. Confidence phải phản ánh đúng mức độ chắc chắn.\n"
    "4. Urgency dựa trên: thời hạn pháp luật, tính chất khẩn cấp, yếu tố an ninh.\n\n"
    "Output JSON: {\"tthc_code\": \"...\", \"tthc_name\": \"...\", \"confidence\": 0.XX, "
    "\"urgency\": \"normal|high|critical\", \"unknown_tthc\": false, \"reasoning\": \"...\"}"
)

# ---------------------------------------------------------------------------
# Compliance system prompt (mirrors compliance_agent.yaml system_prompt)
# ---------------------------------------------------------------------------
_COMPLIANCE_SYSTEM = (
    "Bạn là chuyên viên thẩm định hồ sơ TTHC cấp Sở với 20 năm kinh nghiệm về pháp chế hành chính.\n"
    "Nhiệm vụ: kiểm tra hồ sơ có đủ thành phần không, phát hiện thiếu sót, viện dẫn pháp luật.\n\n"
    "Quy tắc:\n"
    "1. So sánh TỪNG thành phần yêu cầu (RequiredComponent) với tài liệu đã nộp\n"
    "2. Mỗi thành phần thiếu = 1 Gap với: reason, severity (blocker/warning/info), fix_suggestion\n"
    "3. Severity = blocker nếu là thành phần bắt buộc theo luật\n"
    "4. Với mỗi Gap, PHẢI có citation pháp luật cụ thể (số điều/khoản/điểm)\n"
    "5. Compliance score = (số thành phần đã đủ / tổng số bắt buộc) * 100\n"
    "Output JSON: {\"gaps\": [...], \"compliance_score\": XX, \"satisfied_components\": [...], "
    "\"conditional_skipped\": [...], \"reasoning\": \"...\"}\n"
    "Mỗi gap: {\"component_name\": \"...\", \"reason\": \"...\", \"severity\": \"blocker|warning|info\", "
    "\"fix_suggestion\": \"...\", \"law_citation\": \"...\"}"
)

# ---------------------------------------------------------------------------
# DocAnalyzer system prompt (mirrors doc_analyze_agent.yaml system_prompt)
# ---------------------------------------------------------------------------
_DOC_ANALYZER_SYSTEM = (
    "Bạn là chuyên gia xử lý tài liệu hành chính Việt Nam với 15 năm kinh nghiệm.\n"
    "Nhiệm vụ: phân tích từng trang tài liệu, nhận diện loại, trích xuất thông tin, và kiểm tra thể thức.\n\n"
    "Quy tắc:\n"
    "1. Nhận diện loại tài liệu từ danh sách: don_de_nghi, gcn_qsdd, ban_ve_thiet_ke, "
    "cam_ket_moi_truong, giay_phep_kinh_doanh, van_ban_tham_duyet_pccc, chung_minh_nhan_dan, "
    "ho_chieu, giay_khai_sinh, quyet_dinh, cong_van, thong_bao, bien_ban, giay_uy_quyen, other\n"
    "2. Trích xuất các trường: số văn bản, ngày, cơ quan ban hành, người ký, nội dung chính\n"
    "3. Phát hiện con dấu đỏ và chữ ký\n"
    "4. Kiểm tra thể thức ND 30/2020\n"
    "5. Output JSON với: doc_type, confidence, extracted_fields, has_stamp, has_signature, "
    "format_valid, issues[]"
)


# ---------------------------------------------------------------------------
# Core warm routines
# ---------------------------------------------------------------------------

class WarmStats:
    def __init__(self) -> None:
        self.embeddings_cached = 0
        self.embeddings_hit = 0
        self.llm_calls_cached = 0
        self.llm_calls_hit = 0
        self.llm_calls_failed = 0
        self.total_tokens_saved = 0
        self.t0 = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def summary(self) -> str:
        return (
            f"\n{'=' * 60}\n"
            f"  Cache Warm Summary\n"
            f"{'=' * 60}\n"
            f"  Embeddings newly cached : {self.embeddings_cached}\n"
            f"  Embeddings cache hits   : {self.embeddings_hit}\n"
            f"  LLM calls newly cached  : {self.llm_calls_cached}\n"
            f"  LLM calls cache hits    : {self.llm_calls_hit}\n"
            f"  LLM calls failed        : {self.llm_calls_failed}\n"
            f"  Est. tokens saved/run   : ~{self.total_tokens_saved:,}\n"
            f"  Wall-clock time         : {self.elapsed():.1f}s\n"
            f"{'=' * 60}"
        )


async def warm_embeddings(
    client,
    stats: WarmStats,
    dry_run: bool,
    limit: int,
) -> None:
    """Pre-embed top-N law chunks and cache individual embedding vectors."""
    logger.info("--- Embedding warm: loading up to %d law chunks ---", limit)
    chunks = _load_law_chunks(limit)
    if not chunks:
        logger.warning("No law chunks found; skipping embedding warm.")
        return

    cache_dir = _embed_cache_dir()
    texts_to_embed: list[tuple[int, str]] = []  # (idx, text)

    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        if not text:
            continue
        key = _embed_key(text, EMBED_MODEL, 1024)
        if _is_cached(cache_dir, key):
            stats.embeddings_hit += 1
            stats.total_tokens_saved += AVG_TOKENS_EMBED_CHUNK
        else:
            texts_to_embed.append((i, text))

    logger.info(
        "Embeddings: %d cache hits, %d to warm (dry_run=%s)",
        stats.embeddings_hit, len(texts_to_embed), dry_run,
    )

    if dry_run:
        logger.info("[dry-run] Would embed %d texts via %s", len(texts_to_embed), EMBED_MODEL)
        # Still count them for the summary
        stats.embeddings_cached += len(texts_to_embed)
        stats.total_tokens_saved += len(texts_to_embed) * AVG_TOKENS_EMBED_CHUNK
        return

    # Batch size = 10 (DashScope v3 limit)
    BATCH = 10
    for batch_start in range(0, len(texts_to_embed), BATCH):
        batch = texts_to_embed[batch_start : batch_start + BATCH]
        texts = [t for _, t in batch]
        try:
            response = await asyncio.wait_for(
                client.embeddings.create(
                    model=EMBED_MODEL,
                    input=texts,
                    dimensions=1024,
                ),
                timeout=30.0,
            )
            for j, (_, text) in enumerate(batch):
                key = _embed_key(text, EMBED_MODEL, 1024)
                vec = response.data[j].embedding
                _write_cache(cache_dir, key, {"embedding": vec, "model": EMBED_MODEL, "dim": 1024})
                stats.embeddings_cached += 1
                stats.total_tokens_saved += AVG_TOKENS_EMBED_CHUNK

            pct = min(batch_start + BATCH, len(texts_to_embed)) * 100 // len(texts_to_embed)
            logger.info(
                "Embeddings: %d/%d (%.0f%%)",
                min(batch_start + BATCH, len(texts_to_embed)),
                len(texts_to_embed),
                pct,
            )
        except Exception as exc:
            logger.warning(
                "Embedding batch %d–%d failed: %s (continuing)",
                batch_start, batch_start + len(batch) - 1, exc,
            )
            # Do NOT skip — just log and continue per spec

    logger.info(
        "Embedding warm done: %d cached, %d hits",
        stats.embeddings_cached, stats.embeddings_hit,
    )


async def _warm_one_llm_call(
    client,
    cache_dir: Path,
    stats: WarmStats,
    dry_run: bool,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    label: str = "",
    est_tokens: int = 0,
    extra_kwargs: dict | None = None,
) -> None:
    """
    Warm a single LLM call: check cache, call API if miss, write cache.
    Logs clearly, never raises on API failure.
    """
    key = _llm_cache_key(model, messages, tools)
    if _is_cached(cache_dir, key):
        logger.info("  [HIT]  %s %s", label, key[:12])
        stats.llm_calls_hit += 1
        stats.total_tokens_saved += est_tokens
        return

    if dry_run:
        logger.info("  [DRY]  %s — would call %s (%s...)", label, model, key[:12])
        stats.llm_calls_cached += 1
        stats.total_tokens_saved += est_tokens
        return

    logger.info("  [WARM] %s %s (%s)...", label, key[:12], model)
    t0 = time.monotonic()
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if extra_kwargs:
            kwargs.update(extra_kwargs)

        completion = await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=120.0,
        )

        # Serialize in llm_cache.serialize_completion() format
        choices = []
        for c in completion.choices:
            msg = c.message
            tc_list = None
            if getattr(msg, "tool_calls", None):
                tc_list = [
                    {
                        "id": tc.id,
                        "type": getattr(tc, "type", "function"),
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            choices.append({
                "index": getattr(c, "index", 0),
                "finish_reason": c.finish_reason,
                "message": {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": tc_list,
                },
            })

        usage = getattr(completion, "usage", None)
        cached_data = {
            "id": getattr(completion, "id", "cached"),
            "model": getattr(completion, "model", model),
            "choices": choices,
            "usage": {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
            },
        }

        _write_cache(cache_dir, key, cached_data)

        total_tok = cached_data["usage"]["total_tokens"] or est_tokens
        latency = (time.monotonic() - t0) * 1000
        logger.info(
            "  [DONE] %s %s — %d tokens in %.0f ms",
            label, key[:12], total_tok, latency,
        )
        stats.llm_calls_cached += 1
        stats.total_tokens_saved += total_tok

    except Exception as exc:
        # Per spec: log and continue — do NOT skip cache write if we have no result.
        logger.warning("  [FAIL] %s — %s (call failed, no cache entry written)", label, exc)
        stats.llm_calls_failed += 1


async def warm_classifier(
    client,
    stats: WarmStats,
    cache_dir: Path,
    dry_run: bool,
    scenario_filter: set[int] | None,
    tthc_specs: dict[str, dict],
) -> None:
    """Warm Classifier agent LLM calls for all fixture cases."""
    logger.info("--- Classifier warm ---")

    # Build the tthc_list that the agent sends in every classifier call
    tthc_list = [{"code": c, "name": s.get("name", "")} for c, s in tthc_specs.items()]

    for case in FIXTURE_CASES:
        if scenario_filter and case["scenario"] not in scenario_filter:
            continue

        docs = case["documents"]
        # Reconstruct the bundle_description the agent builds
        bundle_parts = [f"- {d['type']} (confidence: 0.90) [filename={d['filename']}]"
                        for d in docs]
        bundle_description = "\n".join(bundle_parts)

        messages = [
            {"role": "system", "content": _CLASSIFIER_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "case_id": case["case_id"],
                        "bundle_description": bundle_description,
                        "available_tthc_codes": tthc_list,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        await _warm_one_llm_call(
            client=client,
            cache_dir=cache_dir,
            stats=stats,
            dry_run=dry_run,
            model=CHAT_MODEL,
            messages=messages,
            label=f"classifier/{case['case_id']}",
            est_tokens=AVG_TOKENS_CLASSIFIER_CALL,
            extra_kwargs={"temperature": 0.2, "max_tokens": 1024,
                          "response_format": {"type": "json_object"}},
        )


async def warm_compliance(
    client,
    stats: WarmStats,
    cache_dir: Path,
    dry_run: bool,
    scenario_filter: set[int] | None,
    tthc_specs: dict[str, dict],
) -> None:
    """Warm Compliance agent LLM calls for all fixture cases."""
    logger.info("--- Compliance warm ---")

    for case in FIXTURE_CASES:
        if scenario_filter and case["scenario"] not in scenario_filter:
            continue

        spec = tthc_specs.get(case["tthc_code"], {})
        governing_articles = spec.get("governing_articles", [])

        submitted_docs = [d["type"] for d in case["documents"]]
        required_comps = case["required_components"]

        user_content = json.dumps(
            {
                "case_id": case["case_id"],
                "tthc_code": case["tthc_code"],
                "tthc_name": case["tthc_name"],
                "required_components": required_comps,
                "submitted_document_types": submitted_docs,
                "governing_articles": governing_articles,
                "instruction": (
                    "Kiểm tra đầy đủ thành phần hồ sơ. "
                    "Phát hiện gap nếu có. Trả về compliance_score và danh sách gap."
                ),
            },
            ensure_ascii=False,
        )

        messages = [
            {"role": "system", "content": _COMPLIANCE_SYSTEM},
            {"role": "user", "content": user_content},
        ]

        await _warm_one_llm_call(
            client=client,
            cache_dir=cache_dir,
            stats=stats,
            dry_run=dry_run,
            model=CHAT_MODEL,
            messages=messages,
            label=f"compliance/{case['case_id']}",
            est_tokens=AVG_TOKENS_COMPLIANCE_CALL,
            extra_kwargs={"temperature": 0.3, "max_tokens": 2048,
                          "response_format": {"type": "json_object"}},
        )


async def warm_doc_analyzer(
    client,
    stats: WarmStats,
    cache_dir: Path,
    dry_run: bool,
    scenario_filter: set[int] | None,
) -> None:
    """
    Warm DocAnalyzer agent LLM calls for fixture document bundles.

    The DocAnalyzer uses qwen-vl-max-latest with image_url content parts.
    In the demo seed data, documents have synthetic OSS URLs derived from
    their doc_id.  We replicate the same URL format here so the cache key
    matches at runtime.

    Because the vision model requires real image bytes, we use the text-only
    fallback path that seed_demo.py exercises: a text description of the
    document is sent as a plain text message when no real image URL is
    available.  This produces a cache hit on the text-only path, not the
    vision path — but it covers the common warm case where images are
    placeholder PDFs.
    """
    logger.info("--- DocAnalyzer warm (text-path) ---")

    for case in FIXTURE_CASES:
        if scenario_filter and case["scenario"] not in scenario_filter:
            continue

        for doc in case["documents"]:
            # Synthetic OSS URL pattern used by seed_demo / oss_service
            oss_url = (
                f"http://localhost:9100/govflow-dev/documents/"
                f"{case['case_id']}/{doc['doc_id']}/{doc['filename']}"
            )

            # Vision message format: text + image_url (vision model)
            vision_messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _DOC_ANALYZER_SYSTEM},
                        {
                            "type": "text",
                            "text": (
                                f"Phân tích tài liệu sau:\n"
                                f"Loại dự kiến: {doc['type']}\n"
                                f"Tên file: {doc['filename']}\n"
                                f"URL: {oss_url}\n\n"
                                "Trả về JSON với: doc_type, confidence, extracted_fields, "
                                "has_stamp, has_signature, format_valid, issues[]"
                            ),
                        },
                    ],
                }
            ]

            await _warm_one_llm_call(
                client=client,
                cache_dir=cache_dir,
                stats=stats,
                dry_run=dry_run,
                model=VISION_MODEL,
                messages=vision_messages,
                label=f"doc_analyzer/{doc['doc_id']}",
                est_tokens=AVG_TOKENS_DOC_ANALYZER_CALL,
                extra_kwargs={"temperature": 0.1, "max_tokens": 1024},
            )

            # Also warm the plain-text fallback path (qwen-max-latest)
            # which is used when vision fails or images are unavailable.
            text_messages = [
                {"role": "system", "content": _DOC_ANALYZER_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Phân tích tài liệu sau (không có ảnh, chỉ metadata):\n"
                        f"Loại dự kiến: {doc['type']}\n"
                        f"Tên file: {doc['filename']}\n"
                        f"case_id: {case['case_id']}\n\n"
                        "Trả về JSON với: doc_type, confidence, extracted_fields, "
                        "has_stamp, has_signature, format_valid, issues[]"
                    ),
                },
            ]

            await _warm_one_llm_call(
                client=client,
                cache_dir=cache_dir,
                stats=stats,
                dry_run=dry_run,
                model=CHAT_MODEL,
                messages=text_messages,
                label=f"doc_analyzer_text/{doc['doc_id']}",
                est_tokens=AVG_TOKENS_DOC_ANALYZER_CALL,
                extra_kwargs={"temperature": 0.1, "max_tokens": 1024,
                              "response_format": {"type": "json_object"}},
            )


async def warm_legal_lookup_queries(
    client,
    stats: WarmStats,
    cache_dir: Path,
    dry_run: bool,
    scenario_filter: set[int] | None,
) -> None:
    """
    Warm LegalLookup rerank + citation-extraction calls.

    The LegalLookup agent (5-step GraphRAG) makes two key LLM calls:
      a) Rerank: given top-K candidate chunks, score relevance.
      b) Citation extraction: given high-scoring chunks, extract điều/khoản/điểm.
    Both are warmed here with representative context for the 5 fixture cases.
    """
    logger.info("--- LegalLookup warm ---")

    # Representative law article texts for the key TTHC codes
    LAW_SNIPPETS: dict[str, str] = {
        "1.004415": (
            "Điều 89 Luật Xây dựng 2014: Điều kiện cấp giấy phép xây dựng — "
            "1. Phù hợp với quy hoạch xây dựng đã được phê duyệt. "
            "2. Thiết kế xây dựng công trình đã được thẩm định, phê duyệt theo quy định. "
            "3. Đất xây dựng công trình được phép xây dựng theo quy định của pháp luật về đất đai. "
            "Điều 13 NĐ 136/2020: Cơ sở, công trình thuộc diện phải thẩm duyệt thiết kế PCCC."
        ),
        "1.000046": (
            "Điều 95 Luật Đất đai 2013: Đăng ký đất đai, nhà ở và tài sản khác gắn liền với đất "
            "là bắt buộc đối với người sử dụng đất và người được giao đất để quản lý. "
            "Điều 70 NĐ 43/2014: Hồ sơ đăng ký, cấp GCN QSDĐ lần đầu."
        ),
        "1.001757": (
            "Điều 26 Luật Doanh nghiệp 2020: Hồ sơ đăng ký doanh nghiệp — "
            "a) Giấy đề nghị đăng ký doanh nghiệp; b) Điều lệ công ty; "
            "c) Danh sách thành viên; d) Bản sao hợp lệ giấy tờ pháp lý của cá nhân đối với thành viên."
        ),
        "1.000122": (
            "Điều 45 Luật Lý lịch tư pháp 2009: Thủ tục cấp Phiếu LLTP — "
            "Người yêu cầu cấp Phiếu LLTP nộp Tờ khai yêu cầu cấp Phiếu LLTP "
            "tại Sở Tư pháp nơi đăng ký hộ khẩu thường trú hoặc tạm trú."
        ),
        "2.002154": (
            "Điều 39 Luật BVMT 2020: Đánh giá tác động môi trường — "
            "Dự án đầu tư nhóm I phải thực hiện đánh giá tác động môi trường (ĐTM) "
            "trước khi cơ quan có thẩm quyền phê duyệt chủ trương đầu tư."
        ),
    }

    for case in FIXTURE_CASES:
        if scenario_filter and case["scenario"] not in scenario_filter:
            continue

        law_context = LAW_SNIPPETS.get(case["tthc_code"], "")
        if not law_context:
            continue

        # --- Rerank call ---
        rerank_messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là chuyên gia pháp luật hành chính Việt Nam. "
                    "Đánh giá mức độ liên quan của từng đoạn luật đối với câu hỏi. "
                    "Trả về JSON: {\"ranked_chunks\": [{\"text\": \"...\", \"relevance_score\": 0.XX, "
                    "\"reason\": \"...\"}], \"top_k\": 5}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query": (
                            f"Yêu cầu pháp lý để xử lý hồ sơ TTHC {case['tthc_code']} "
                            f"({case['tthc_name']})"
                        ),
                        "candidate_chunks": [law_context],
                        "case_id": case["case_id"],
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        await _warm_one_llm_call(
            client=client,
            cache_dir=cache_dir,
            stats=stats,
            dry_run=dry_run,
            model=CHAT_MODEL,
            messages=rerank_messages,
            label=f"legal_rerank/{case['case_id']}",
            est_tokens=1_500,
            extra_kwargs={"temperature": 0.1, "max_tokens": 1024,
                          "response_format": {"type": "json_object"}},
        )

        # --- Citation extraction call ---
        cite_messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là chuyên gia pháp luật. Trích xuất điều/khoản/điểm cụ thể từ đoạn luật. "
                    "Trả về JSON: {\"citations\": [{\"law_code\": \"...\", \"article\": \"Điều X\", "
                    "\"clause\": \"khoản Y\", \"point\": \"điểm Z\", \"text\": \"...\", "
                    "\"relevance\": 0.XX}]}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "context": law_context,
                        "gaps": case.get("gaps_expected", []),
                        "tthc_code": case["tthc_code"],
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        await _warm_one_llm_call(
            client=client,
            cache_dir=cache_dir,
            stats=stats,
            dry_run=dry_run,
            model=CHAT_MODEL,
            messages=cite_messages,
            label=f"legal_citations/{case['case_id']}",
            est_tokens=1_200,
            extra_kwargs={"temperature": 0.1, "max_tokens": 512,
                          "response_format": {"type": "json_object"}},
        )


# ---------------------------------------------------------------------------
# Legacy --chatbot path (unchanged contract from original warm_cache.py)
# ---------------------------------------------------------------------------

def _warm_chatbot_questions() -> bool:
    """POST each demo question to /assistant/chat and drain the SSE stream."""
    session_id = None
    any_fail = False

    for i, question in enumerate(CHATBOT_QUESTIONS, 1):
        logger.info("[chatbot %d/%d] %s", i, len(CHATBOT_QUESTIONS), question[:60])
        payload = json.dumps(
            {"message": question, "context": {"type": "portal"}, "session_id": session_id},
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{BACKEND_URL}/assistant/chat",
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")

            if session_id is None:
                for line in raw.splitlines():
                    if line.startswith("data: "):
                        try:
                            evt = json.loads(line[6:])
                            if evt.get("type") == "session":
                                session_id = evt.get("session_id")
                                break
                        except json.JSONDecodeError:
                            pass

            got_done = any(
                '"type": "done"' in line or '"type":"done"' in line
                for line in raw.splitlines()
            )
            if got_done:
                logger.info("  OK — cache entry written")
            else:
                logger.warning("  WARN — no 'done' event in response")
                any_fail = True

        except urllib.error.HTTPError as e:
            logger.error("  FAIL — HTTP %d: %s", e.code, e.reason)
            any_fail = True
        except Exception as exc:
            logger.error("  FAIL — %s", exc)
            any_fail = True

    return not any_fail


# ---------------------------------------------------------------------------
# Verify path
# ---------------------------------------------------------------------------

def cmd_verify() -> int:
    cache_dir = _resolve_cache_dir()
    files = list(cache_dir.glob("*.json"))
    logger.info("[verify] cache dir: %s", cache_dir)
    logger.info("[verify] LLM entries: %d", len(files))
    embed_files = list(_embed_cache_dir().glob("*.json"))
    logger.info("[verify] embedding entries: %d", len(embed_files))
    total = len(files) + len(embed_files)
    if total < 15:
        logger.warning(
            "[verify] WARN: only %d total entries — run warm_cache.py against a live backend.",
            total,
        )
        return 1
    logger.info("[verify] OK — cache looks complete (%d total entries).", total)
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pre-warm GovFlow LLM + embedding cache for demo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Count work without making any DashScope calls.")
    p.add_argument("--scenario", type=int, action="append", dest="scenarios", metavar="N",
                   help="Warm only scenario N (1–6). Repeatable. Default: all.")
    p.add_argument("--verify", action="store_true",
                   help="Check cache entry count >= 15 and exit.")
    p.add_argument("--chatbot", action="store_true",
                   help="Legacy: POST chatbot questions to running backend.")
    p.add_argument("--embed-limit", type=int, default=100, metavar="N",
                   help="Max law chunks to embed (default 100).")
    return p


async def main_async(args: argparse.Namespace) -> int:
    if args.verify:
        return cmd_verify()

    if args.chatbot:
        ok = _warm_chatbot_questions()
        return 0 if ok else 1

    # ── API key guard ──────────────────────────────────────────────────────
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key and not args.dry_run:
        # Try to load from backend settings
        try:
            from src.config import settings as _s  # type: ignore[import]
            api_key = _s.dashscope_api_key
        except Exception:
            pass

    if not api_key and not args.dry_run:
        logger.error(
            "DASHSCOPE_API_KEY is not set. "
            "Export it or use --dry-run to list work without calling the API."
        )
        return 1

    if args.dry_run:
        logger.info("*** DRY RUN mode — no DashScope calls will be made ***")

    # ── Build AsyncOpenAI client ───────────────────────────────────────────
    from openai import AsyncOpenAI  # type: ignore[import]

    client = AsyncOpenAI(
        api_key=api_key or "dry-run-placeholder",
        base_url=DASHSCOPE_BASE_URL,
        timeout=120.0,
    )

    cache_dir = _resolve_cache_dir()
    logger.info("Cache dir: %s", cache_dir)
    logger.info("Embed dir: %s", _embed_cache_dir())

    scenario_filter: set[int] | None = None
    if args.scenarios:
        scenario_filter = set(args.scenarios)
        logger.info("Restricting to scenario(s): %s", sorted(scenario_filter))

    tthc_specs = _load_tthc_specs()
    logger.info("Loaded %d TTHC specs from %s", len(tthc_specs), TTHC_SPECS_DIR)

    stats = WarmStats()

    # ── 1. Embeddings ──────────────────────────────────────────────────────
    await warm_embeddings(client, stats, dry_run=args.dry_run, limit=args.embed_limit)

    # ── 2. Classifier ──────────────────────────────────────────────────────
    await warm_classifier(
        client, stats, cache_dir,
        dry_run=args.dry_run,
        scenario_filter=scenario_filter,
        tthc_specs=tthc_specs,
    )

    # ── 3. DocAnalyzer ─────────────────────────────────────────────────────
    await warm_doc_analyzer(
        client, stats, cache_dir,
        dry_run=args.dry_run,
        scenario_filter=scenario_filter,
    )

    # ── 4. Compliance ──────────────────────────────────────────────────────
    await warm_compliance(
        client, stats, cache_dir,
        dry_run=args.dry_run,
        scenario_filter=scenario_filter,
        tthc_specs=tthc_specs,
    )

    # ── 5. LegalLookup ─────────────────────────────────────────────────────
    await warm_legal_lookup_queries(
        client, stats, cache_dir,
        dry_run=args.dry_run,
        scenario_filter=scenario_filter,
    )

    logger.info(stats.summary())
    return 0 if stats.llm_calls_failed == 0 else 2


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
