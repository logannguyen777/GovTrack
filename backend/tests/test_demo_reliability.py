"""
Demo reliability test: run the exact demo scenario 5x consecutive.
Verify 100% pass rate — no flaky failures allowed.

Requires: Docker services + DashScope API key.
"""

import pytest

from tests.conftest import requires_dashscope

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestDemoReliability:

    @pytest.fixture
    async def demo_client(self, app_client, auth_headers_admin):
        """Pre-authenticated admin client for demo tests."""
        app_client.headers.update(auth_headers_admin)
        yield app_client

    async def test_permission_demo_scene_a(self, demo_client):
        """Scene A: SDK Guard rejects Summary agent reading national_id."""
        resp = await demo_client.post("/demo/permissions/scene-a/sdk-guard-rejection")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DENIED", f"Scene A should deny, got: {data}"
        assert data["tier"] == "SDK_GUARD"
        assert "PROPERTY_FORBIDDEN" in data.get("violation", "")

    async def test_permission_demo_scene_b(self, demo_client):
        """Scene B: RBAC rejects LegalSearch agent creating Gap vertex."""
        resp = await demo_client.post("/demo/permissions/scene-b/rbac-rejection")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DENIED", f"Scene B should deny, got: {data}"
        assert data["tier"] == "GDB_RBAC"

    async def test_permission_demo_scene_c(self, demo_client):
        """Scene C: Property mask dissolves on clearance elevation."""
        resp = await demo_client.post("/demo/permissions/scene-c/clearance-elevation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OK", f"Scene C failed: {data}"
        assert len(data["dissolved_fields"]) > 0, "No fields dissolved"
        # Verify specific masking behavior
        before = data["before_elevation"]
        after = data["after_elevation"]
        assert before["national_id"] == "[REDACTED]"
        assert after["national_id"] == "[REDACTED]"  # REDACT never dissolves
        assert "CLASSIFIED" in before["home_address"]
        assert after["home_address"] == "12 Le Loi, Q1, TP.HCM"  # Dissolved

    @pytest.mark.parametrize("run_number", range(5))
    async def test_permission_scenes_consecutive(self, demo_client, run_number):
        """Run all 3 permission scenes 5 times back-to-back for reliability."""
        # Scene A
        resp = await demo_client.post("/demo/permissions/scene-a/sdk-guard-rejection")
        assert resp.json()["status"] == "DENIED", f"Run {run_number}: Scene A failed"

        # Scene B
        resp = await demo_client.post("/demo/permissions/scene-b/rbac-rejection")
        assert resp.json()["status"] == "DENIED", f"Run {run_number}: Scene B failed"

        # Scene C
        resp = await demo_client.post("/demo/permissions/scene-c/clearance-elevation")
        result = resp.json()
        assert result["status"] == "OK", f"Run {run_number}: Scene C failed"
        assert len(result["dissolved_fields"]) > 0, f"Run {run_number}: no fields dissolved"

    @requires_dashscope
    @pytest.mark.parametrize("run_number", range(5))
    async def test_full_demo_scenario_consecutive(self, demo_client, run_number):
        """
        Full demo scenario: case creation + permission scenes.
        Executed 5 times back-to-back for reliability.
        """
        # Step 1: Create case
        resp = await demo_client.post("/cases", json={
            "tthc_code": "1.004415",
            "department_id": "dept-xaydung",
            "applicant_name": f"Demo User Run {run_number}",
            "applicant_id_number": f"07920100{run_number:04d}",
        })
        assert resp.status_code == 201, f"Run {run_number}: case creation failed: {resp.text}"
        case_id = resp.json()["case_id"]

        # Step 2: Create bundle
        resp = await demo_client.post(f"/cases/{case_id}/bundles", json={
            "files": [
                {"filename": "don_xin.pdf", "content_type": "application/pdf", "size_bytes": 1024},
                {"filename": "banve.pdf", "content_type": "application/pdf", "size_bytes": 2048},
            ],
        })
        assert resp.status_code == 201, f"Run {run_number}: bundle creation failed"

        # Step 3: Permission scenes (these don't need DashScope)
        resp = await demo_client.post("/demo/permissions/scene-a/sdk-guard-rejection")
        assert resp.json()["status"] == "DENIED", f"Run {run_number}: Scene A failed"

        resp = await demo_client.post("/demo/permissions/scene-b/rbac-rejection")
        assert resp.json()["status"] == "DENIED", f"Run {run_number}: Scene B failed"

        resp = await demo_client.post("/demo/permissions/scene-c/clearance-elevation")
        assert resp.json()["status"] == "OK", f"Run {run_number}: Scene C failed"

        # Step 4: Verify case exists
        resp = await demo_client.get(f"/cases/{case_id}")
        assert resp.status_code == 200, f"Run {run_number}: case retrieval failed"
        assert resp.json()["tthc_code"] == "1.004415"
