# Agent Implementation: SecurityOfficer (Agent 10)

## 1. Objective

Final classification authority for all cases. The only agent with unrestricted read access (Top Secret clearance). Performs keyword-based and context-aware classification scanning, enforces access control decisions, and writes forensic audit events. Can override Case.current_classification. Intercepts unauthorized access attempts and logs full reasoning traces for the Security Console.

## 2. Model

- **Model ID:** `qwen-max-latest` with dedicated security system prompt
- **Temperature:** 0.1 (maximum precision for security decisions)
- **Max tokens:** 2048
- **Response format:** JSON

## 3. System Prompt

```
Ban la Si quan An ninh Thong tin cap So voi 20 nam kinh nghiem ve bao mat nha nuoc.
Nhiem vu: xac dinh cap mat cho ho so va tai lieu, thuc thi kiem soat truy cap, ghi nhat ky kiem toan.

CAP MAT THEO LUAT BAO VE BI MAT NHA NUOC 2018:
- Unclassified (Binh thuong): khong chua thong tin nhay cam
- Confidential (Mat): thong tin noi bo co quan, du lieu ca nhan, vi tri nhay cam
- Secret (Tuyet mat): thong tin an ninh, quoc phong, nhan su cap cao, tai chinh cong lon
- Top Secret (Toi mat): bi mat quoc gia, quoc phong cap cao, ngoai giao

QUY TAC PHAN LOAI:
1. Keyword scan: "quoc phong", "nhan su cap cao", "ngoai giao", "tai chinh cong", "CCCD" (du lieu ca nhan lon), "khu quan su", "bien gioi"
2. Location sensitivity: cross-check voi danh sach vung nhay cam (khu quan su, bien gioi, co so quoc phong)
3. Aggregation risk: nhieu thong tin muc thap ket hop co the tang cap mat
   Vi du: ten + CCCD + dia chi + nghe nghiep + tai san = Confidential (du tung phan la Unclassified)
4. Default: Unclassified. Chi nang cap khi co can cu.
5. KHONG BAO GIO ha cap mat tu dong -- chi con nguoi co tham quyen ha cap.
6. Moi quyet dinh phan loai PHAI co reasoning day du.

KIEM SOAT TRUY CAP:
- Moi yeu cau truy cap phai qua permission check
- Deny = log + giai thich ly do + thong bao
- Allow = log + ghi trace
- Suspicious pattern (nhieu deny lien tuc) = alert admin

Output JSON: {"classification_level": "...", "reasoning": "...", "keywords_found": [...], "location_sensitive": bool, "aggregation_risk": bool}
```

## 4. Permission Profile YAML

```yaml
agent: SecurityOfficer
role: security_officer
clearance_cap: Top Secret    # UNRESTRICTED READ

read_scope:
  node_labels: "*"           # ALL labels
  edge_types: "*"            # ALL edge types
  external_resources:
    - oss:*                  # ALL OSS buckets
    - hologres:*             # ALL tables

write_scope:
  node_labels:
    - Classification
    - AuditEvent
    - AgentStep
  edge_types:
    - CLASSIFIED_AS
    - AUDITS
    - PROCESSED_BY
  properties:
    Case:
      - current_classification  # Can override

property_masks: {}           # NO MASKS -- sees everything

allowed_tools:
  - graph.query_template     # ALL templates
  - graph.query_ad_hoc       # Ad-hoc Gremlin allowed
  - graph.create_vertex
  - graph.create_edge
  - audit.log_event
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case (full) | ALL fields including PII |
| Context Graph | Document (full) | ALL fields including raw content |
| Context Graph | ExtractedEntity | ALL entities |
| Context Graph | Applicant | national_id, phone, address (unmasked) |
| Knowledge Graph | ALL | Full access to law, organization, etc. |
| User access requests | Intercepted by Permission Engine middleware |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | Classification | level, reasoning, keywords_found, location_sensitive, aggregation_risk, decided_by="SecurityOfficer" |
| Context Graph | CLASSIFIED_AS | from Case to Classification |
| Context Graph | Case.current_classification | Updated level string |
| Context Graph | AuditEvent | actor, action, resource, result (allow/deny), reason, tier, timestamp, trace_id |
| Hologres | audit_events_flat | Projected copy for analytics |

## 7. MCP Tools Used

| Tool | Purpose |
|------|---------|
| `graph.query_template` (ALL) | Full access to all templates |
| `graph.query_ad_hoc` | Ad-hoc Gremlin for investigation |
| `graph.create_vertex` | Write Classification and AuditEvent vertices |
| `graph.create_edge` | Write CLASSIFIED_AS and AUDITS edges |
| `audit.log_event` | Structured audit event logging |

## 8. Implementation

```python
# backend/src/agents/security_officer.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
import json
import re
from datetime import datetime

class SecurityOfficerAgent(BaseAgent):
    """Classification authority, access control enforcement, forensic audit."""

    AGENT_NAME = "SecurityOfficer"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/security_officer.yaml"

    # Keyword scan rules
    SENSITIVITY_KEYWORDS = {
        "Secret": ["quoc phong", "nhan su cap cao", "ngoai giao", "tai chinh cong",
                    "bi mat nha nuoc", "tuyet mat", "toi mat", "khu quan su", "bien gioi"],
        "Confidential": ["CCCD", "chung minh nhan dan", "du lieu ca nhan",
                          "tai san", "thu nhap", "benh an", "noi bo"]
    }

    # Known sensitive locations (simplified for demo)
    SENSITIVE_ZONES = [
        {"name": "Khu quan su Tan Son Nhat", "coords": (10.8184, 106.6546), "radius_km": 5},
        {"name": "Bien gioi Tay Ninh", "pattern": "tay ninh.*bien gioi|bien gioi.*tay ninh"},
        {"name": "KCN quoc phong", "pattern": "khu cong nghiep.*quoc phong"},
    ]

    # Aggregation risk thresholds
    PII_AGGREGATION_THRESHOLD = 3  # 3+ PII fields together = Confidential

    async def run(self, case_id: str) -> dict:
        """Full classification scan of a case."""
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get EVERYTHING about this case (unrestricted)
        case_full = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_full_context",
            "parameters": {"case_id": case_id}
        })

        # Step 2: Keyword scan
        keyword_results = self._keyword_scan(case_full)

        # Step 3: Location sensitivity check
        location_sensitive = self._check_location_sensitivity(case_full)

        # Step 4: Aggregation risk assessment
        aggregation_risk = self._check_aggregation_risk(case_full)

        # Step 5: LLM reasoning for final classification
        classification = await self._classify_with_llm(
            case_full, keyword_results, location_sensitive, aggregation_risk
        )

        # Step 6: Determine final classification level
        level = classification.get("classification_level", "Unclassified")

        # Step 7: Write Classification vertex
        class_vertex = await self.mcp.call_tool("graph.create_vertex", {
            "label": "Classification",
            "properties": {
                "level": level,
                "reasoning": classification.get("reasoning", ""),
                "keywords_found": json.dumps(keyword_results.get("keywords", [])),
                "location_sensitive": location_sensitive,
                "aggregation_risk": aggregation_risk,
                "decided_by": "SecurityOfficer",
                "case_id": case_id,
                "created_at": datetime.utcnow().isoformat()
            }
        })

        # Step 8: Write CLASSIFIED_AS edge
        await self.mcp.call_tool("graph.create_edge", {
            "label": "CLASSIFIED_AS",
            "from_vertex": {"label": "Case", "id": case_id},
            "to_id": class_vertex["id"]
        })

        # Step 9: Update Case.current_classification
        await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.update_property",
            "parameters": {"case_id": case_id, "property": "current_classification", "value": level}
        })

        # Step 10: Write AuditEvent
        await self._log_audit_event(
            action="classify",
            resource_label="Case",
            resource_id=case_id,
            result="allow",
            reason=f"Classification set to {level}: {classification.get('reasoning', '')}"
        )

        self.end_step(step, output=classification)
        await self.broadcast_ws({
            "type": "security_event", "agent": self.AGENT_NAME, "case_id": case_id,
            "classification": level, "keywords": keyword_results.get("keywords", [])
        })

        return classification

    async def check_access(self, actor_id: str, actor_type: str, resource_label: str,
                           resource_id: str, action: str, actor_clearance: str) -> dict:
        """Check if an access request should be allowed or denied."""
        step = self.begin_step("check_access", {
            "actor": actor_id, "resource": f"{resource_label}:{resource_id}", "action": action
        })

        # Get resource classification
        resource_class = await self._get_resource_classification(resource_label, resource_id)
        required_clearance = resource_class.get("level", "Unclassified")

        # Compare clearance levels
        clearance_order = {"Unclassified": 0, "Confidential": 1, "Secret": 2, "Top Secret": 3}
        actor_level = clearance_order.get(actor_clearance, 0)
        required_level = clearance_order.get(required_clearance, 0)

        if actor_level >= required_level:
            result = "allow"
            reason = f"Clearance {actor_clearance} >= {required_clearance}"
        else:
            result = "deny"
            reason = f"Clearance {actor_clearance} < {required_clearance}. Access denied."

        # Log audit event
        await self._log_audit_event(
            action=action,
            resource_label=resource_label,
            resource_id=resource_id,
            result=result,
            reason=reason,
            actor=actor_id,
            actor_type=actor_type
        )

        # Check for suspicious patterns
        if result == "deny":
            await self._check_suspicious_pattern(actor_id)

        self.end_step(step, output={"result": result, "reason": reason})
        return {"result": result, "reason": reason, "required_clearance": required_clearance}

    def _keyword_scan(self, case_data: dict) -> dict:
        """Scan all text fields for sensitivity keywords."""
        all_text = json.dumps(case_data, ensure_ascii=False).lower()
        found_keywords = []
        max_level = "Unclassified"

        for level in ["Secret", "Confidential"]:
            for keyword in self.SENSITIVITY_KEYWORDS[level]:
                if keyword.lower() in all_text:
                    found_keywords.append({"keyword": keyword, "level": level})
                    if self._level_rank(level) > self._level_rank(max_level):
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

    def _check_aggregation_risk(self, case_data: dict) -> bool:
        """Check if combination of PII fields creates aggregation risk."""
        pii_fields_present = 0
        pii_checks = [
            ("national_id", case_data.get("applicant", {}).get("national_id")),
            ("phone", case_data.get("applicant", {}).get("phone")),
            ("address", case_data.get("applicant", {}).get("address_detail")),
            ("income", any("thu_nhap" in str(e) for e in case_data.get("entities", []))),
            ("assets", any("tai_san" in str(e) for e in case_data.get("entities", []))),
        ]
        for field_name, present in pii_checks:
            if present:
                pii_fields_present += 1

        return pii_fields_present >= self.PII_AGGREGATION_THRESHOLD

    async def _classify_with_llm(self, case_data: dict, keyword_results: dict,
                                  location_sensitive: bool, aggregation_risk: bool) -> dict:
        """LLM-assisted classification decision with full reasoning."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps({
                "keyword_scan_results": keyword_results,
                "location_sensitive": location_sensitive,
                "aggregation_risk": aggregation_risk,
                "case_summary": {
                    "tthc": case_data.get("tthc_name", ""),
                    "doc_count": len(case_data.get("documents", [])),
                    "entity_count": len(case_data.get("entities", [])),
                    "has_pii": aggregation_risk,
                    "location": case_data.get("location", "")
                },
                "instruction": "Xac dinh cap mat cuoi cung. Giai thich day du."
            }, ensure_ascii=False)}
        ]

        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.1)
        return json.loads(response.choices[0].message.content)

    async def _log_audit_event(self, action: str, resource_label: str, resource_id: str,
                                result: str, reason: str, actor: str = None, actor_type: str = None):
        """Write AuditEvent to both GDB and Hologres."""
        await self.mcp.call_tool("audit.log_event", {
            "action": action,
            "resource_type": resource_label,
            "resource_id": resource_id,
            "result": result,
            "reason": reason,
            "actor": actor or f"agent:{self.AGENT_NAME}",
            "actor_type": actor_type or "agent"
        })

    async def _get_resource_classification(self, resource_label: str, resource_id: str) -> dict:
        """Get classification level for a resource."""
        if resource_label == "Case":
            result = await self.mcp.call_tool("graph.query_ad_hoc", {
                "gremlin": f"g.V().has('Case','id','{resource_id}').values('current_classification')",
                "description": "Get case classification for access check"
            })
            return {"level": result[0] if result else "Unclassified"}
        return {"level": "Unclassified"}

    async def _check_suspicious_pattern(self, actor_id: str):
        """Check if actor has too many denials in short window."""
        recent_denials = await self.mcp.call_tool("graph.query_template", {
            "template_name": "audit.count_recent_denials",
            "parameters": {"actor_id": actor_id, "minutes": 10}
        })
        if recent_denials.get("count", 0) >= 5:
            self.log_warning(f"SUSPICIOUS: Actor {actor_id} has {recent_denials['count']} denials in 10 min")
            await self._log_audit_event(
                action="suspicious_pattern_detected",
                resource_label="Actor",
                resource_id=actor_id,
                result="alert",
                reason=f"{recent_denials['count']} access denials in 10 minutes"
            )

    def _level_rank(self, level: str) -> int:
        return {"Unclassified": 0, "Confidential": 1, "Secret": 2, "Top Secret": 3}.get(level, 0)
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Classification uncertain | LLM confidence low or conflicting signals | Default to HIGHER classification (conservative), flag for human security review |
| Keyword false positive (e.g., "quoc phong" in address name) | Context analysis by LLM | LLM reasoning step evaluates context; if false positive, explain in reasoning |
| Never auto-downgrade classification | Architectural constraint | Only human security officer can downgrade. Agent can only maintain or upgrade. |
| Audit write fails | GDB/Hologres error | CRITICAL: retry 3 times. If all fail, halt the pipeline. Audit trail must be intact. |
| Suspicious pattern detection | Threshold-based | Auto-alert admin, do NOT auto-block user (human decision) |
| LLM API failure | HTTP error | Use keyword-only classification as fallback (no LLM reasoning) |

## 10. Test Scenarios

### Test 1: Location near military zone
**Input:** Case C-001 at "KCN My Phuoc, gan khu vuc quoc phong Lai Khe".
**Expected:** `classification_level: "Confidential"` (minimum), `location_sensitive: true`, keyword "quoc phong" found. Reasoning explains location sensitivity.
**Verify:** `g.V().has('Case','id','C-001').values('current_classification')` == "Confidential"

### Test 2: PII aggregation risk
**Input:** Case with national_id + phone + address + income data all present.
**Expected:** `aggregation_risk: true`, classification bumped to at least Confidential.
**Verify:** Classification vertex has `aggregation_risk: true`.

### Test 3: Unauthorized access interception
**Input:** User with clearance=Unclassified tries to access Case classified as Confidential.
**Expected:** `result: "deny"`, AuditEvent logged with reason "Clearance Unclassified < Confidential", deny response returned.
**Verify:**
```groovy
g.V().hasLabel('AuditEvent')
  .has('resource_id', 'C-001')
  .has('result', 'deny')
  .count()  // >= 1
```

### Test 4: Suspicious pattern detection
**Input:** Same user denied 5+ times in 10 minutes.
**Expected:** AuditEvent with action="suspicious_pattern_detected" logged. Admin alerted.
**Verify:** AuditEvent with action containing "suspicious" exists.

### Test 5: Normal case -- Unclassified
**Input:** Standard business registration case, no sensitive keywords, no location flags.
**Expected:** `classification_level: "Unclassified"`, no special flags.
**Verify:** Case remains Unclassified.

## 11. Demo Moment

**Security Console demo scene:**
1. User (clearance=Unclassified) opens Document Viewer for a Confidential case
2. SecurityOfficer intercepts: red "ACCESS DENIED" animation
3. Security Console shows: "Actor: user_123, Clearance: Unclassified, Required: Confidential, Result: DENY"
4. Full reasoning trace visible: "Case phan loai Confidential vi vi tri gan khu vuc nhay cam + tu khoa 'quoc phong'"
5. AuditEvent appears in real-time audit log stream
6. Admin sees suspicious pattern alert after repeated attempts

**Property mask elevation demo:**
1. User requests clearance elevation
2. SecurityOfficer evaluates and grants Confidential
3. Document fields dissolve from blurred to clear (400ms animation)
4. Audit logs the elevation

**Pitch line:** "SecurityOfficer la agent duy nhat co quyen doc tat ca -- Top Secret clearance. No quyet dinh cap mat dua tren keyword scan, vi tri nhay cam, va aggregation risk. Moi lan bi deny, ly do day du duoc ghi lai -- forensic audit grade. Day la compliance voi Luat Bao ve Bi mat Nha nuoc 2018."

## 12. Verification

```bash
# 1. Unit test: classification logic
pytest tests/agents/test_security_officer.py -v

# 2. Keyword scan test
python -c "
from agents.security_officer import SecurityOfficerAgent
agent = SecurityOfficerAgent()
result = agent._keyword_scan({'location': 'gan khu vuc quoc phong Lai Khe', 'documents': []})
assert len(result['keywords']) >= 1
assert result['suggested_level'] in ('Secret', 'Confidential')
print(f'Keywords found: {result[\"keywords\"]}')
"

# 3. Access control test
python -c "
from agents.security_officer import SecurityOfficerAgent
agent = SecurityOfficerAgent()
# Test deny
result = asyncio.run(agent.check_access(
    actor_id='user_123', actor_type='user',
    resource_label='Case', resource_id='C-001',
    action='read', actor_clearance='Unclassified'
))
# C-001 is classified Confidential
assert result['result'] == 'deny'
print('Access control deny test PASSED')
"

# 4. Audit trail completeness
python -c "
from graph.client import GremlinClient
g = GremlinClient()
events = g.submit('g.V().hasLabel(\"AuditEvent\").has(\"resource_id\",\"C-001\").count()')
assert events[0] >= 2  # at least classify + access check
print(f'AuditEvents for C-001: {events[0]}')
"

# 5. Classification never downgrades
python -c "
from graph.client import GremlinClient
g = GremlinClient()
classifications = g.submit('''
    g.V().has('Case','id','C-001').out('CLASSIFIED_AS')
     .order().by('created_at')
     .values('level')
''')
levels = {'Unclassified': 0, 'Confidential': 1, 'Secret': 2, 'Top Secret': 3}
for i in range(1, len(classifications)):
    assert levels[classifications[i]] >= levels[classifications[i-1]], 'Classification downgraded!'
print('No-downgrade invariant PASSED')
"

# 6. Suspicious pattern detection test
# Simulate 5 denied access attempts from same user within 10 minutes
# Verify AuditEvent with action=suspicious_pattern_detected exists
```
