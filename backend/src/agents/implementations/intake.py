"""
backend/src/agents/implementations/intake.py
Intake Agent: receives documents, runs OCR, extracts basic entities.
"""
from __future__ import annotations

import json
from typing import Any

from ...database import async_gremlin_submit
from ..base import BaseAgent
from ..orchestrator import register_agent


class IntakeAgent(BaseAgent):
    """Intake processor agent."""
    profile_name = "intake_agent"

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Build messages with case context."""
        # Fetch case data
        case_data = await async_gremlin_submit(
            "g.V().has('Case', 'case_id', cid).valueMap(true)", {"cid": case_id},
        )
        documents = await async_gremlin_submit(
            "g.V().has('Case', 'case_id', cid)"
            ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
            ".valueMap(true)",
            {"cid": case_id},
        )

        # Fetch TTHC spec if available
        tthc_code = ""
        if case_data:
            tthc_code = case_data[0].get("tthc_code", [""])[0]
        tthc_spec = {}
        if tthc_code:
            specs = await async_gremlin_submit(
                "g.V().has('TTHCSpec', 'code', code).valueMap(true)",
                {"code": tthc_code},
            )
            if specs:
                tthc_spec = specs[0]

        context = {
            "case_id": case_id,
            "case": case_data[0] if case_data else {},
            "documents": documents,
            "tthc_spec": tthc_spec,
        }

        return [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Tiep nhan ho so: {case_id}\n\n"
                    f"Thong tin ho so:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
                    "Hay thuc hien cac buoc:\n"
                    "1. Kiem tra danh sach tai lieu da nop (dung tool case_documents)\n"
                    "2. Voi moi tai lieu, lay signed URL (dung tool oss_get_url) "
                    "va trich xuat thong tin co ban\n"
                    "3. Ghi nhan ket qua vao AgentStep (dung tool add_agent_step)\n"
                    "4. Ghi audit log (dung tool audit_log)\n"
                    "5. Tra ve tom tat thong tin da trich xuat"
                ),
            },
        ]


# Register with orchestrator
register_agent("intake_agent", IntakeAgent)
