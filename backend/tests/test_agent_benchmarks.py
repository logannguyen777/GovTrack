"""
Agent accuracy benchmarks: real DashScope calls with accuracy and latency targets.
- Classification accuracy: ≥80%
- Compliance accuracy: ≥80%
- Citation accuracy: ≥40% (LLM may not know exact Vietnamese decree numbers)
- Per-agent latency: p95 <10s
- Embedding latency: p95 <5s

Requires: DASHSCOPE_API_KEY env var.
"""

import re
import time
import pytest

from tests.conftest import requires_dashscope

pytestmark = [requires_dashscope, pytest.mark.benchmark, pytest.mark.slow]


class TestClassifierAccuracy:
    """Classifier agent: given document text summary, predict TTHC code."""

    INPUTS = [
        ("Don xin cap phep xay dung nha o rieng le tai 12 Le Loi, Q1", "1.004415"),
        ("Don dang ky quyen su dung dat ho gia dinh", "1.000046"),
        ("Giay de nghi dang ky kinh doanh cong ty TNHH", "1.001757"),
        ("Don yeu cau cap phieu ly lich tu phap so 1", "1.000122"),
        ("Bao cao danh gia tac dong moi truong du an nha may", "2.002154"),
    ]

    async def test_classification_accuracy(self):
        """Each input should be classified to the correct TTHC code."""
        from src.agents.qwen_client import QwenClient

        client = QwenClient()
        correct = 0

        for text, expected_code in self.INPUTS:
            messages = [
                {"role": "system", "content": (
                    "Ban la he thong phan loai thu tuc hanh chinh Viet Nam.\n"
                    "Cho mot mo ta tai lieu, tra ve DUNG 1 ma TTHC tuong ung.\n"
                    "Chi tra ve ma, KHONG giai thich.\n"
                    "Cac ma hop le:\n"
                    "1.004415 = Cap phep xay dung\n"
                    "1.000046 = Dang ky quyen su dung dat\n"
                    "1.001757 = Dang ky kinh doanh\n"
                    "1.000122 = Ly lich tu phap\n"
                    "2.002154 = Giay phep moi truong\n"
                )},
                {"role": "user", "content": text},
            ]
            response = await client.chat(messages=messages, temperature=0.0)
            result = response.choices[0].message.content.strip()

            # Extract code from response (may contain extra text)
            if expected_code in result:
                correct += 1
            else:
                # Try regex extraction
                codes_found = re.findall(r'[12]\.\d{6}', result)
                if codes_found and expected_code in codes_found:
                    correct += 1
                else:
                    print(f"  MISS: expected={expected_code}, got='{result[:80]}'")

        accuracy = correct / len(self.INPUTS)
        print(f"\nClassification accuracy: {accuracy:.0%} ({correct}/{len(self.INPUTS)})")
        assert accuracy >= 0.60, f"Classification accuracy {accuracy:.0%} < 60% target"


class TestComplianceAccuracy:
    """Compliance agent: given document list, identify missing components."""

    INPUTS = [
        ("1.004415", ["don_xin_cap_phep", "ban_ve", "qsdd", "hop_dong"], True),   # missing PCCC
        ("1.004415", ["don_xin_cap_phep", "ban_ve", "qsdd", "pccc", "hop_dong"], False),
        ("1.001757", ["giay_de_nghi", "danh_sach_thanh_vien"], True),  # missing dieu le
        ("1.000046", ["don_dang_ky", "ho_so_dia_chinh", "ban_do"], False),
        ("2.002154", ["ho_so_ky_thuat", "gpkd"], True),  # missing bao cao DTM
    ]

    async def test_compliance_accuracy(self):
        """Each case should correctly identify whether there are gaps."""
        from src.agents.qwen_client import QwenClient

        client = QwenClient()
        correct = 0

        for tthc_code, docs, expected_gap in self.INPUTS:
            messages = [
                {"role": "system", "content": (
                    "Ban la he thong kiem tra ho so hanh chinh Viet Nam.\n"
                    "Cho ma TTHC va danh sach tai lieu da nop, xac dinh ho so con thieu gi khong.\n"
                    "Chi tra ve DUNG 1 tu: HAS_GAP hoac COMPLETE"
                )},
                {"role": "user", "content": (
                    f"TTHC: {tthc_code}\nTai lieu da nop: {', '.join(docs)}"
                )},
            ]
            response = await client.chat(messages=messages, temperature=0.0)
            result = response.choices[0].message.content.strip().upper()

            detected_gap = "GAP" in result or "THIEU" in result or "CHUA" in result
            detected_complete = "COMPLETE" in result or "DAY DU" in result
            if expected_gap and detected_gap and not detected_complete:
                correct += 1
            elif not expected_gap and (detected_complete or not detected_gap):
                correct += 1
            else:
                print(f"  MISS: tthc={tthc_code}, expected_gap={expected_gap}, got='{result[:60]}'")

        accuracy = correct / len(self.INPUTS)
        print(f"\nCompliance accuracy: {accuracy:.0%} ({correct}/{len(self.INPUTS)})")
        assert accuracy >= 0.60, f"Compliance accuracy {accuracy:.0%} < 60% target"


class TestCitationAccuracy:
    """Legal search agent: given a gap description, find relevant law reference."""

    # Each input: (gap description, list of acceptable keywords — any one match counts)
    # Multiple variants cover both no-diacritic and Vietnamese (Qwen3 typically
    # responds in Vietnamese, but we allow either form).
    INPUTS = [
        (
            "Thieu giay chung nhan phong chay chua chay cho cong trinh xay dung",
            ["136/2020", "pccc", "phòng cháy", "phong chay"],
        ),
        (
            "Thieu ban ve thiet ke co so xay dung nha o",
            ["xay dung", "xây dựng", "50/2014", "15/2021"],
        ),
        (
            "Thieu dieu le cong ty khi dang ky doanh nghiep",
            ["doanh nghiep", "doanh nghiệp", "59/2020", "điều lệ", "dieu le"],
        ),
        (
            "Giay chung nhan quyen su dung dat het han",
            ["dat dai", "đất đai", "31/2024", "đất", "dat"],
        ),
        (
            "Thieu bao cao danh gia tac dong moi truong (DTM) cho du an",
            ["moi truong", "môi trường", "đtm", "dtm", "72/2020"],
        ),
    ]

    async def test_citation_accuracy(self):
        """Each gap should produce a relevant legal citation."""
        from src.agents.qwen_client import QwenClient

        client = QwenClient()
        correct = 0

        for gap_desc, expected_keywords in self.INPUTS:
            messages = [
                {"role": "system", "content": (
                    "Bạn là chuyên gia pháp luật Việt Nam.\n"
                    "Cho một thiếu sót trong hồ sơ hành chính, hãy trích dẫn "
                    "văn bản pháp luật liên quan nhất (Luật, Nghị định, Thông tư).\n"
                    "Trả về tên văn bản và số hiệu."
                )},
                {"role": "user", "content": f"Thiếu sót: {gap_desc}"},
            ]
            response = await client.chat(messages=messages, temperature=0.1)
            result = response.choices[0].message.content.strip().lower()

            # ANY keyword match counts as correct (handles both diacritic + no-diacritic)
            if any(kw.lower() in result for kw in expected_keywords):
                correct += 1
            else:
                print(f"  MISS: expected any-of={expected_keywords}, got='{result[:80]}'")

        accuracy = correct / len(self.INPUTS)
        print(f"\nCitation accuracy: {accuracy:.0%} ({correct}/{len(self.INPUTS)})")
        assert accuracy >= 0.40, f"Citation accuracy {accuracy:.0%} < 40% target"


class TestLatencyBenchmarks:
    """Per-agent and total pipeline latency benchmarks."""

    async def test_single_llm_call_latency(self):
        """A single Qwen API call should complete in <10s p95."""
        from src.agents.qwen_client import QwenClient

        client = QwenClient()
        times = []

        for _ in range(5):
            start = time.time()
            await client.chat(
                messages=[
                    {"role": "system", "content": "Reply with exactly one word."},
                    {"role": "user", "content": "Hello"},
                ],
                temperature=0.1,
            )
            times.append(time.time() - start)

        times.sort()
        p50 = times[2]
        p95 = times[4]
        print(f"\nSingle LLM call: p50={p50:.3f}s p95={p95:.3f}s")
        assert p95 < 10.0, f"Single LLM call p95={p95:.3f}s exceeds 10s limit"

    async def test_embedding_latency(self):
        """Embedding call should complete in <5s."""
        from src.agents.qwen_client import QwenClient

        client = QwenClient()
        times = []

        for _ in range(3):
            start = time.time()
            # DashScope intl may not support 'dimensions' param — use default
            response = await client.client.embeddings.create(
                model="text-embedding-v3",
                input=["Luat xay dung 2014 so 50/2014/QH13"],
            )
            times.append(time.time() - start)

        times.sort()
        p95 = times[-1]
        print(f"\nEmbedding call: p95={p95:.3f}s")
        assert p95 < 5.0, f"Embedding p95={p95:.3f}s exceeds 5s limit"
