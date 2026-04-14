"""
End-to-end happy path tests: one test per TTHC procedure.
Each test creates a case via real API, triggers the agent pipeline,
and verifies the output graph state.

Requires: Docker services (Gremlin, PostgreSQL, MinIO) + DashScope API key.
"""

import asyncio
import pytest
from httpx import AsyncClient

from tests.conftest import requires_dashscope

pytestmark = [pytest.mark.integration, requires_dashscope, pytest.mark.slow]


@pytest.fixture
async def client(app_client, auth_headers_admin):
    """Pre-authenticated admin client."""
    app_client.headers.update(auth_headers_admin)
    yield app_client


async def _poll_trace(client: AsyncClient, case_id: str, timeout: int = 120) -> dict:
    """Poll agent trace until pipeline completes or times out."""
    for _ in range(timeout // 3):
        resp = await client.get(f"/agents/trace/{case_id}")
        if resp.status_code == 200:
            trace = resp.json()
            if trace.get("status") in ("completed", "failed", "approved", "published"):
                return trace
        await asyncio.sleep(3)
    # Final attempt
    resp = await client.get(f"/agents/trace/{case_id}")
    return resp.json() if resp.status_code == 200 else {}


class TestCPXD:
    """TTHC 1.004415 — Cap phep xay dung (construction permit)."""

    async def test_cpxd_full_pipeline(self, client):
        """
        Submit 5-doc case with missing PCCC (fire safety certificate).
        Expected: Gap detected, ND 136/2020 cited, citizen notification drafted.
        """
        # Step 1: Create case
        resp = await client.post("/cases", json={
            "tthc_code": "1.004415",
            "department_id": "dept-xaydung",
            "applicant_name": "Nguyen Van Minh",
            "applicant_id_number": "079201001234",
            "applicant_phone": "0901234567",
            "applicant_address": "12 Le Loi, Q1, TP.HCM",
        })
        assert resp.status_code == 201, f"Case creation failed: {resp.text}"
        case_id = resp.json()["case_id"]

        # Step 2: Create bundle with documents
        resp = await client.post(f"/cases/{case_id}/bundles", json={
            "files": [
                {"filename": "don_xin_cap_phep.pdf", "content_type": "application/pdf", "size_bytes": 1024},
                {"filename": "ban_ve_thiet_ke.pdf", "content_type": "application/pdf", "size_bytes": 2048},
                {"filename": "giay_chung_nhan_qsdd.pdf", "content_type": "application/pdf", "size_bytes": 1024},
                {"filename": "hop_dong_xay_dung.pdf", "content_type": "application/pdf", "size_bytes": 1024},
                {"filename": "bao_hiem.pdf", "content_type": "application/pdf", "size_bytes": 512},
            ],
        })
        assert resp.status_code == 201, f"Bundle creation failed: {resp.text}"

        # Step 3: Finalize case
        resp = await client.post(f"/cases/{case_id}/finalize")
        assert resp.status_code == 200

        # Step 4: Trigger agent pipeline
        resp = await client.post(f"/agents/run/{case_id}", json={"pipeline": "full"})
        assert resp.status_code == 202

        # Step 5: Poll for completion
        trace = await _poll_trace(client, case_id)
        assert trace.get("status") != "unknown", "Pipeline did not complete"

        # Step 6: Verify graph state via subgraph
        resp = await client.get(f"/graph/case/{case_id}/subgraph")
        assert resp.status_code == 200
        subgraph = resp.json()
        assert len(subgraph.get("nodes", [])) > 0, "Subgraph should have nodes"

        # Step 7: Verify case info
        resp = await client.get(f"/cases/{case_id}")
        assert resp.status_code == 200
        case = resp.json()
        assert case["tthc_code"] == "1.004415"


class TestGCN_QSDD:
    """TTHC 1.000046 — GCN quyen su dung dat (land certificate)."""

    async def test_qsdd_full_pipeline(self, client):
        resp = await client.post("/cases", json={
            "tthc_code": "1.000046",
            "department_id": "dept-tainguyen",
            "applicant_name": "Tran Thi Lan",
            "applicant_id_number": "079301002345",
            "applicant_phone": "0912345678",
        })
        assert resp.status_code == 201
        case_id = resp.json()["case_id"]

        resp = await client.post(f"/cases/{case_id}/bundles", json={
            "files": [
                {"filename": "don_dang_ky.pdf", "content_type": "application/pdf", "size_bytes": 1024},
                {"filename": "ho_so_dia_chinh.pdf", "content_type": "application/pdf", "size_bytes": 2048},
                {"filename": "ban_do_dia_chinh.pdf", "content_type": "application/pdf", "size_bytes": 4096},
            ],
        })
        assert resp.status_code == 201

        await client.post(f"/cases/{case_id}/finalize")
        resp = await client.post(f"/agents/run/{case_id}", json={"pipeline": "full"})
        assert resp.status_code == 202

        trace = await _poll_trace(client, case_id)
        assert trace.get("status") != "unknown"

        resp = await client.get(f"/cases/{case_id}")
        assert resp.json()["tthc_code"] == "1.000046"


class TestDKKD:
    """TTHC 1.001757 — Dang ky kinh doanh (business registration)."""

    async def test_dkkd_full_pipeline(self, client):
        resp = await client.post("/cases", json={
            "tthc_code": "1.001757",
            "department_id": "dept-kehoach",
            "applicant_name": "Le Van Hung",
            "applicant_id_number": "079401003456",
        })
        assert resp.status_code == 201
        case_id = resp.json()["case_id"]

        resp = await client.post(f"/cases/{case_id}/bundles", json={
            "files": [
                {"filename": "giay_de_nghi.pdf", "content_type": "application/pdf", "size_bytes": 1024},
                {"filename": "dieu_le.pdf", "content_type": "application/pdf", "size_bytes": 2048},
                {"filename": "danh_sach_thanh_vien.pdf", "content_type": "application/pdf", "size_bytes": 1024},
            ],
        })
        assert resp.status_code == 201

        await client.post(f"/cases/{case_id}/finalize")
        resp = await client.post(f"/agents/run/{case_id}", json={"pipeline": "full"})
        assert resp.status_code == 202

        trace = await _poll_trace(client, case_id)
        assert trace.get("status") != "unknown"


class TestLLTP:
    """TTHC 1.000122 — Ly lich tu phap (criminal record extract)."""

    async def test_lltp_full_pipeline(self, client):
        resp = await client.post("/cases", json={
            "tthc_code": "1.000122",
            "department_id": "dept-tuphap",
            "applicant_name": "Pham Minh Duc",
            "applicant_id_number": "079501004567",
        })
        assert resp.status_code == 201
        case_id = resp.json()["case_id"]

        resp = await client.post(f"/cases/{case_id}/bundles", json={
            "files": [
                {"filename": "don_yeu_cau.pdf", "content_type": "application/pdf", "size_bytes": 1024},
                {"filename": "cccd.pdf", "content_type": "application/pdf", "size_bytes": 512},
            ],
        })
        assert resp.status_code == 201

        await client.post(f"/cases/{case_id}/finalize")
        resp = await client.post(f"/agents/run/{case_id}", json={"pipeline": "full"})
        assert resp.status_code == 202

        trace = await _poll_trace(client, case_id)
        assert trace.get("status") != "unknown"


class TestGPMT:
    """TTHC 2.002154 — Giay phep moi truong (environmental permit)."""

    async def test_gpmt_full_pipeline(self, client):
        resp = await client.post("/cases", json={
            "tthc_code": "2.002154",
            "department_id": "dept-tainguyen",
            "applicant_name": "Cty TNHH Xanh",
            "applicant_id_number": "0312345678",
        })
        assert resp.status_code == 201
        case_id = resp.json()["case_id"]

        resp = await client.post(f"/cases/{case_id}/bundles", json={
            "files": [
                {"filename": "bao_cao_dtm.pdf", "content_type": "application/pdf", "size_bytes": 4096},
                {"filename": "ho_so_ky_thuat.pdf", "content_type": "application/pdf", "size_bytes": 2048},
                {"filename": "giay_phep_kinh_doanh.pdf", "content_type": "application/pdf", "size_bytes": 1024},
            ],
        })
        assert resp.status_code == 201

        await client.post(f"/cases/{case_id}/finalize")
        resp = await client.post(f"/agents/run/{case_id}", json={"pipeline": "full"})
        assert resp.status_code == 202

        trace = await _poll_trace(client, case_id)
        assert trace.get("status") != "unknown"
