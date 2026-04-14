"""
backend/src/agents/implementations/security_officer.py
SecurityOfficer Agent (Agent 10): Final classification authority for all cases.
The only agent with unrestricted read access (Top Secret clearance).

Pipeline:
  1. Fetch full case context (all docs, entities, applicant) -- unrestricted
  2. Keyword scan for sensitivity terms (quoc phong, nhan su cap cao, etc.)
  3. Location sensitivity check against known sensitive zones
  4. Aggregation risk assessment (PII field accumulation)
  5. Fetch existing classification (no-downgrade invariant)
  6. Single LLM call for final classification with full reasoning
  7. Enforce no-downgrade: max(existing, new)
  8. Write Classification vertex + CLASSIFIED_AS edge + update Case
  9. Write AuditEvent, log step, broadcast

Also provides check_access() for access control enforcement.
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from ...database import async_gremlin_submit, pg_connection
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.security_officer")


class SecurityOfficerAgent(BaseAgent):
    """Classification authority, access control enforcement, forensic audit."""

    profile_name = "security_officer_agent"

    # Clearance level ordering
    CLEARANCE_ORDER: dict[str, int] = {
        "Unclassified": 0,
        "Confidential": 1,
        "Secret": 2,
        "Top Secret": 3,
    }

    # Keyword scan rules -- checked highest-severity first
    SENSITIVITY_KEYWORDS: dict[str, list[str]] = {
        "Secret": [
            "quoc phong", "nhan su cap cao", "ngoai giao", "tai chinh cong",
            "bi mat nha nuoc", "tuyet mat", "toi mat", "khu quan su", "bien gioi",
        ],
        "Confidential": [
            "CCCD", "chung minh nhan dan", "du lieu ca nhan",
            "tai san", "thu nhap", "benh an", "noi bo",
        ],
    }

    # Known sensitive locations (simplified for demo)
    SENSITIVE_ZONES: list[dict[str, Any]] = [
        {"name": "Khu quan su Tan Son Nhat", "pattern": r"tan son nhat.*quan su|quan su.*tan son nhat"},
        {"name": "Bien gioi Tay Ninh", "pattern": r"tay ninh.*bien gioi|bien gioi.*tay ninh"},
        {"name": "KCN quoc phong", "pattern": r"khu cong nghiep.*quoc phong|kcn.*quoc phong"},
        {"name": "Khu vuc quoc phong", "pattern": r"khu vuc.*quoc phong|quoc phong.*khu vuc"},
        {"name": "Bien gioi", "pattern": r"bien gioi"},
        {"name": "Khu quan su", "pattern": r"khu quan su"},
    ]

    # 3+ PII fields together -> aggregation risk
    PII_AGGREGATION_THRESHOLD = 3

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    # ------------------------------------------------------------------
    # Main entry: classify a case
    # ------------------------------------------------------------------

    async def run(self, case_id: str) -> AgentResult:
        """
        Full classification scan of a case.
        Override BaseAgent.run() for deterministic pipeline.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[SecurityOfficer] Starting classification on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # -- Step 1: Fetch full case context (unrestricted) --
            case_context = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".project('case', 'applicant', 'documents', 'classification')"
                ".by(valueMap(true))"
                ".by(out('SUBMITTED_BY').valueMap(true).fold())"
                ".by(out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                ".project('doc', 'entities')"
                ".by(valueMap(true))"
                ".by(out('EXTRACTED').valueMap('field_name', 'value').fold())"
                ".fold())"
                ".by(coalesce(out('CLASSIFIED_AS').valueMap(true).fold(), constant([])))",
                {"cid": case_id},
            )

            if not case_context:
                raise ValueError(f"Case {case_id} not found in graph")

            ctx = case_context[0]
            case_data = ctx.get("case", {})
            applicant_list = ctx.get("applicant", [])
            applicant_data = applicant_list[0] if applicant_list else {}
            documents = ctx.get("documents", [])

            logger.info(
                f"[SecurityOfficer] Case {case_id}: "
                f"{len(documents)} docs, applicant={'yes' if applicant_data else 'no'}"
            )

            # -- Step 2: Keyword scan --
            # Build a flat text blob from all case data for scanning
            scan_data = {
                "case": case_data,
                "applicant": applicant_data,
                "documents": documents,
            }
            keyword_results = self._keyword_scan(scan_data)
            logger.info(
                f"[SecurityOfficer] Keywords: {len(keyword_results['keywords'])} found, "
                f"suggested={keyword_results['suggested_level']}"
            )

            # -- Step 3: Location sensitivity --
            location_sensitive = self._check_location_sensitivity(scan_data)

            # -- Step 4: Aggregation risk --
            aggregation_risk = self._check_aggregation_risk(scan_data, applicant_data)

            # -- Step 5: Get existing classification (no-downgrade) --
            existing_level = "Unclassified"
            try:
                existing = await async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".values('current_classification')",
                    {"cid": case_id},
                )
                if existing:
                    existing_level = str(existing[0])
            except Exception:
                pass  # No existing classification = Unclassified

            # -- Step 6: LLM classification --
            tthc_name = self._extract_prop(case_data, "tthc_code") or ""
            location = self._extract_prop(case_data, "location") or ""

            classification = await self._classify_with_llm(
                keyword_results=keyword_results,
                location_sensitive=location_sensitive,
                aggregation_risk=aggregation_risk,
                tthc_name=tthc_name,
                doc_count=len(documents),
                location=location,
            )

            llm_level = classification.get("classification_level", "Unclassified")

            # -- Step 7: Enforce no-downgrade --
            final_level = self._max_level(existing_level, llm_level)

            # Also consider keyword suggestion (conservative)
            keyword_suggested = keyword_results.get("suggested_level", "Unclassified")
            final_level = self._max_level(final_level, keyword_suggested)

            # Aggregation risk bumps to at least Confidential
            if aggregation_risk and self.CLEARANCE_ORDER.get(final_level, 0) < 1:
                final_level = "Confidential"

            # Location sensitivity bumps to at least Confidential
            if location_sensitive and self.CLEARANCE_ORDER.get(final_level, 0) < 1:
                final_level = "Confidential"

            classification["classification_level"] = final_level

            logger.info(
                f"[SecurityOfficer] Final classification: {final_level} "
                f"(existing={existing_level}, llm={llm_level}, keyword={keyword_suggested})"
            )

            # -- Step 8: Write Classification vertex + edge --
            cls_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()
            keywords_json = json.dumps(keyword_results.get("keywords", []), ensure_ascii=False)

            await async_gremlin_submit(
                "g.addV('Classification')"
                ".property('classification_id', cls_id)"
                ".property('level', level)"
                ".property('reasoning', reasoning)"
                ".property('keywords_found', keywords)"
                ".property('location_sensitive', loc_sens)"
                ".property('aggregation_risk', agg_risk)"
                ".property('decided_by', decided_by)"
                ".property('case_id', case_id)"
                ".property('created_at', ts)"
                ".as('cls')"
                ".V().has('Case', 'case_id', case_id).addE('CLASSIFIED_AS').to('cls')",
                {
                    "cls_id": cls_id,
                    "level": final_level,
                    "reasoning": classification.get("reasoning", ""),
                    "keywords": keywords_json,
                    "loc_sens": str(location_sensitive),
                    "agg_risk": str(aggregation_risk),
                    "decided_by": "SecurityOfficer",
                    "case_id": case_id,
                    "ts": now,
                },
            )

            # -- Step 9: Update Case.current_classification --
            await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".property('current_classification', level)",
                {"cid": case_id, "level": final_level},
            )

            # -- Step 10: Write AuditEvent --
            await self._write_audit_event(
                event_type="classify",
                actor_id=f"agent:{self.profile.name}",
                target_type="Case",
                target_id=case_id,
                case_id=case_id,
                details=json.dumps({
                    "level": final_level,
                    "reasoning": classification.get("reasoning", "")[:500],
                    "keywords": keyword_results.get("keywords", []),
                    "location_sensitive": location_sensitive,
                    "aggregation_risk": aggregation_risk,
                }, ensure_ascii=False),
            )

            # -- Step 11: Log step, broadcast, return --
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_security_officer",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            output_data = {
                "classification_level": final_level,
                "reasoning": classification.get("reasoning", ""),
                "keywords_found": keyword_results.get("keywords", []),
                "location_sensitive": location_sensitive,
                "aggregation_risk": aggregation_risk,
                "existing_level": existing_level,
                "no_downgrade_applied": (
                    self.CLEARANCE_ORDER.get(existing_level, 0)
                    > self.CLEARANCE_ORDER.get(llm_level, 0)
                ),
            }
            output_summary = json.dumps(output_data, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "classification": final_level,
                "keywords": [k["keyword"] for k in keyword_results.get("keywords", [])],
                "duration_ms": round(duration_ms),
            })

            # WebSocket security event for Security Console
            await self._broadcast(case_id, "security_event", {
                "agent": self.profile.name,
                "case_id": case_id,
                "classification": final_level,
                "keywords": keyword_results.get("keywords", []),
                "location_sensitive": location_sensitive,
                "aggregation_risk": aggregation_risk,
            })

            logger.info(
                f"[SecurityOfficer] Case {case_id}: classification={final_level}, "
                f"duration={round(duration_ms)}ms"
            )

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="completed",
                output=output_summary,
                tool_calls_count=0,
                usage=usage,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"[SecurityOfficer] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_security_officer",
                usage=self.client.reset_usage(),
                duration_ms=duration_ms,
                status="failed",
                error=str(e),
            )

            await self._broadcast(case_id, "agent_failed", {
                "agent_name": self.profile.name,
                "error": str(e),
            })

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="failed",
                output="",
                duration_ms=duration_ms,
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Access control entry point
    # ------------------------------------------------------------------

    async def check_access(
        self,
        actor_id: str,
        actor_type: str,
        resource_label: str,
        resource_id: str,
        action: str,
        actor_clearance: str,
    ) -> dict[str, Any]:
        """
        Check if an access request should be allowed or denied.
        Called by the permission middleware or API layer.
        """
        logger.info(
            f"[SecurityOfficer] Access check: {actor_type}:{actor_id} -> "
            f"{action} {resource_label}:{resource_id} (clearance={actor_clearance})"
        )

        # Get resource classification
        required_clearance = await self._get_resource_classification(
            resource_label, resource_id
        )

        # Compare clearance levels
        actor_level = self.CLEARANCE_ORDER.get(actor_clearance, 0)
        required_level = self.CLEARANCE_ORDER.get(required_clearance, 0)

        if actor_level >= required_level:
            result = "allow"
            reason = f"Clearance {actor_clearance} >= {required_clearance}"
        else:
            result = "deny"
            reason = (
                f"Clearance {actor_clearance} < {required_clearance}. "
                f"Access denied."
            )

        # Log audit event
        await self._write_audit_event(
            event_type="access_check",
            actor_id=actor_id,
            target_type=resource_label,
            target_id=resource_id,
            case_id=resource_id if resource_label == "Case" else "",
            details=json.dumps({
                "action": action,
                "actor_type": actor_type,
                "actor_clearance": actor_clearance,
                "required_clearance": required_clearance,
                "result": result,
                "reason": reason,
            }, ensure_ascii=False),
        )

        # Check for suspicious patterns on deny
        if result == "deny":
            await self._check_suspicious_pattern(actor_id)

        logger.info(
            f"[SecurityOfficer] Access {result}: {reason}"
        )

        return {
            "result": result,
            "reason": reason,
            "required_clearance": required_clearance,
        }

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def _keyword_scan(self, case_data: dict) -> dict[str, Any]:
        """Scan all text fields for sensitivity keywords."""
        all_text = json.dumps(case_data, ensure_ascii=False).lower()
        found_keywords: list[dict[str, str]] = []
        max_level = "Unclassified"

        # Check highest severity first
        for level in ["Secret", "Confidential"]:
            for keyword in self.SENSITIVITY_KEYWORDS[level]:
                if keyword.lower() in all_text:
                    found_keywords.append({"keyword": keyword, "level": level})
                    if self.CLEARANCE_ORDER.get(level, 0) > self.CLEARANCE_ORDER.get(max_level, 0):
                        max_level = level

        return {"keywords": found_keywords, "suggested_level": max_level}

    def _check_location_sensitivity(self, case_data: dict) -> bool:
        """Check if case location is in a sensitive zone."""
        location_text = json.dumps(case_data, ensure_ascii=False).lower()

        for zone in self.SENSITIVE_ZONES:
            if "pattern" in zone:
                if re.search(zone["pattern"], location_text, re.IGNORECASE):
                    return True
            if "name" in zone and zone["name"].lower() in location_text:
                return True

        return False

    def _check_aggregation_risk(self, case_data: dict, applicant_data: dict) -> bool:
        """Check if combination of PII fields creates aggregation risk."""
        pii_fields_present = 0
        all_text = json.dumps(case_data, ensure_ascii=False).lower()

        pii_checks = [
            self._extract_prop(applicant_data, "national_id"),
            self._extract_prop(applicant_data, "phone"),
            self._extract_prop(applicant_data, "address_detail")
            or self._extract_prop(applicant_data, "address"),
            "thu_nhap" in all_text or "thu nhap" in all_text,
            "tai_san" in all_text or "tai san" in all_text,
        ]

        for present in pii_checks:
            if present:
                pii_fields_present += 1

        return pii_fields_present >= self.PII_AGGREGATION_THRESHOLD

    async def _classify_with_llm(
        self,
        keyword_results: dict,
        location_sensitive: bool,
        aggregation_risk: bool,
        tthc_name: str,
        doc_count: int,
        location: str,
    ) -> dict[str, Any]:
        """LLM-assisted classification decision with full reasoning."""
        user_content = json.dumps({
            "keyword_scan_results": keyword_results,
            "location_sensitive": location_sensitive,
            "aggregation_risk": aggregation_risk,
            "case_summary": {
                "tthc": tthc_name,
                "doc_count": doc_count,
                "has_pii": aggregation_risk,
                "location": location,
            },
            "instruction": "Xac dinh cap mat cuoi cung. Giai thich day du.",
        }, ensure_ascii=False)

        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {"role": "user", "content": user_content},
        ]

        # Retry loop with JSON parse fallback (same as ComplianceAgent)
        for attempt in range(2):
            try:
                completion = await self.client.chat(
                    messages=messages,
                    model=self.profile.model,
                    temperature=0.1,
                    max_tokens=2048,
                    response_format={"type": "json_object"},
                )

                content = completion.choices[0].message.content or ""

                # Strip markdown fences if present
                cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
                cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

                result = json.loads(cleaned)

                # Validate required fields
                if "classification_level" not in result:
                    result["classification_level"] = keyword_results.get(
                        "suggested_level", "Unclassified"
                    )
                if "reasoning" not in result:
                    result["reasoning"] = ""

                return result

            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning(
                        "[SecurityOfficer] Invalid JSON from Qwen, retrying"
                    )
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Output KHONG hop le JSON. Tra lai DUNG FORMAT: "
                            '{"classification_level": "Unclassified|Confidential|Secret|Top Secret", '
                            '"reasoning": "...", "keywords_found": [...], '
                            '"location_sensitive": bool, "aggregation_risk": bool}'
                        ),
                    })

            except Exception as e:
                logger.warning(
                    f"[SecurityOfficer] LLM call failed (attempt {attempt + 1}): {e}"
                )

        # Fallback: keyword-only classification (no LLM reasoning)
        logger.warning(
            "[SecurityOfficer] LLM classification failed, using keyword-only fallback"
        )
        return {
            "classification_level": keyword_results.get("suggested_level", "Unclassified"),
            "reasoning": (
                "Fallback: phan loai dua tren keyword scan. "
                "LLM khong kha dung. Can kiem tra lai."
            ),
            "keywords_found": keyword_results.get("keywords", []),
            "location_sensitive": location_sensitive,
            "aggregation_risk": aggregation_risk,
        }

    # ------------------------------------------------------------------
    # Access control helpers
    # ------------------------------------------------------------------

    async def _get_resource_classification(
        self, resource_label: str, resource_id: str
    ) -> str:
        """Get classification level for a resource."""
        # Map resource types to their ID property
        id_property_map: dict[str, str] = {
            "Case": "case_id",
            "Document": "doc_id",
            "Draft": "draft_id",
        }

        prop_key = id_property_map.get(resource_label)
        if not prop_key:
            return "Unclassified"

        try:
            result = await async_gremlin_submit(
                f"g.V().has('{resource_label}', '{prop_key}', rid)"
                ".values('current_classification')",
                {"rid": resource_id},
            )
            if result:
                return str(result[0])
        except Exception as e:
            logger.warning(
                f"[SecurityOfficer] Failed to get classification for "
                f"{resource_label}:{resource_id}: {e}"
            )

        return "Unclassified"

    async def _check_suspicious_pattern(self, actor_id: str) -> None:
        """Check if actor has too many denials in short window."""
        try:
            # Fetch recent audit events for this actor
            recent_events = await async_gremlin_submit(
                "g.V().hasLabel('AuditEvent')"
                ".has('actor_id', aid)"
                ".has('event_type', 'access_check')"
                ".valueMap('timestamp', 'details')",
                {"aid": actor_id},
            )

            if not recent_events:
                return

            # Filter for deny results in last 10 minutes
            now = datetime.now(UTC)
            deny_count = 0

            for event in recent_events:
                details_raw = self._extract_prop(event, "details")
                if not details_raw:
                    continue

                try:
                    details = json.loads(details_raw)
                except (json.JSONDecodeError, TypeError):
                    continue

                if details.get("result") != "deny":
                    continue

                # Check timestamp (within 10 minutes)
                ts_str = self._extract_prop(event, "timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if (now - ts).total_seconds() <= 600:
                            deny_count += 1
                    except (ValueError, TypeError):
                        deny_count += 1  # Conservative: count if can't parse time

            if deny_count >= 5:
                logger.warning(
                    f"[SecurityOfficer] SUSPICIOUS: Actor {actor_id} has "
                    f"{deny_count} denials in 10 minutes"
                )

                await self._write_audit_event(
                    event_type="suspicious_pattern_detected",
                    actor_id=f"agent:{self.profile.name}",
                    target_type="Actor",
                    target_id=actor_id,
                    case_id="",
                    details=json.dumps({
                        "denial_count": deny_count,
                        "window_minutes": 10,
                        "actor_id": actor_id,
                        "alert": "Nhieu lan truy cap bi tu choi trong thoi gian ngan",
                    }, ensure_ascii=False),
                )

                # Broadcast alert for Security Console
                await self._broadcast("system", "security_alert", {
                    "type": "suspicious_pattern",
                    "actor_id": actor_id,
                    "denial_count": deny_count,
                    "window_minutes": 10,
                })

        except Exception as e:
            logger.warning(
                f"[SecurityOfficer] Suspicious pattern check failed: {e}"
            )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _write_audit_event(
        self,
        event_type: str,
        actor_id: str,
        target_type: str,
        target_id: str,
        case_id: str,
        details: str,
    ) -> None:
        """Write AuditEvent to GDB and Hologres with retry."""
        now = datetime.now(UTC).isoformat()

        # GDB -- retry 3 times (audit trail must be intact)
        for attempt in range(3):
            try:
                await async_gremlin_submit(
                    "g.addV('AuditEvent')"
                    ".property('event_type', et)"
                    ".property('actor_id', actor)"
                    ".property('target_type', tt)"
                    ".property('target_id', tid)"
                    ".property('timestamp', ts)"
                    ".property('details', det)",
                    {
                        "et": event_type,
                        "actor": actor_id,
                        "tt": target_type,
                        "tid": target_id,
                        "ts": now,
                        "det": details,
                    },
                )
                break
            except Exception as e:
                if attempt == 2:
                    logger.error(
                        f"[SecurityOfficer] CRITICAL: Audit GDB write failed "
                        f"after 3 retries: {e}"
                    )
                    raise RuntimeError(
                        f"Audit trail integrity compromised: {e}"
                    ) from e
                logger.warning(
                    f"[SecurityOfficer] Audit GDB write retry {attempt + 1}: {e}"
                )

        # Hologres -- best-effort (non-blocking)
        try:
            async with pg_connection() as conn:
                await conn.execute(
                    "INSERT INTO audit_events_flat "
                    "(event_type, actor_id, actor_name, "
                    "target_type, target_id, case_id, details) "
                    "VALUES ($1, $2::uuid, $3, $4, $5, $6, $7::jsonb)",
                    event_type, actor_id or None, "",
                    target_type, target_id, case_id, details,
                )
        except Exception as e:
            logger.warning(f"[SecurityOfficer] Audit Hologres write failed: {e}")

    def _max_level(self, a: str, b: str) -> str:
        """Return the higher classification level."""
        if self.CLEARANCE_ORDER.get(a, 0) >= self.CLEARANCE_ORDER.get(b, 0):
            return a
        return b

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap result (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""

    @staticmethod
    def _extract_bool(vertex_map: dict, key: str, default: bool = True) -> bool:
        """Extract a boolean property from Gremlin valueMap result."""
        val = vertex_map.get(key, default)
        if isinstance(val, list):
            val = val[0] if val else default
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)


# Register with orchestrator
register_agent("security_officer_agent", SecurityOfficerAgent)
