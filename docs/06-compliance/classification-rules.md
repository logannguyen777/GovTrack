# Classification Rules — SecurityOfficer reasoning

The `SecurityOfficer` agent is the only entity that decides classification level for a case. Its reasoning rules follow Luật BVBMNN 2018 + common-sense sensitivity analysis.

## 4-level classification (from Luật BVBMNN 2018)

| Level | Vietnamese | Description | % of TTHC cases |
|---|---|---|---|
| **Unclassified** | (default, không phải mật) | Thông tin công khai, không gây tổn hại | ~95% |
| **Confidential (Mật)** | Mật | Gây tổn hại cho lợi ích nhà nước | ~4% |
| **Secret (Tối mật)** | Tối mật | Gây tổn hại nghiêm trọng | ~0.9% |
| **Top Secret (Tuyệt mật)** | Tuyệt mật | Gây tổn hại đặc biệt nghiêm trọng | ~0.1% |

Most TTHC for citizens/SMEs are **Unclassified** (cấp phép XD thông thường, ĐKKD, LLTP). They become classified when:
- Applicant/Project location is in sensitive geographic zone
- Content touches state secrets (defense, intelligence, high-level personnel)
- Aggregation of multiple low-sensitivity items creates higher sensitivity

## Rule engine

### Rule 1 — Location sensitivity

```python
def check_location_sensitivity(entities):
    """Check if project location is in sensitive zone."""
    location = extract_location(entities)

    if location.near_military_zone(radius_km=5):
        return 'Confidential', 'Location within 5km of military installation'

    if location.near_government_compound(radius_km=2):
        return 'Confidential', 'Location near government compound'

    if location.in_border_area(distance_km=50):
        return 'Confidential', 'Location in border zone'

    if location.near_strategic_infrastructure():  # power, water, telecom backbone
        return 'Confidential', 'Near strategic infrastructure'

    return 'Unclassified', None
```

**Implementation:** `SecurityOfficer` cross-checks `ExtractedEntity[location]` against geographic KG data (sensitive zones stored as polygon geometries or point features in KG).

### Rule 2 — Content keyword scan

```python
SENSITIVE_KEYWORDS = {
    'defense': ['quốc phòng', 'quân sự', 'vũ khí', 'căn cứ'],  # Confidential+
    'intelligence': ['tình báo', 'an ninh', 'điệp báo'],  # Secret+
    'diplomacy': ['ngoại giao', 'công tác nước ngoài', 'đại sứ quán'],  # Confidential
    'high_personnel': ['Bộ trưởng', 'Thứ trưởng', 'UV BCT', 'UV TW'],  # Confidential
    'finance_classified': ['ngân sách quốc phòng', 'dự trữ ngoại hối'],  # Secret+
    'nuclear': ['hạt nhân', 'plutonium', 'uranium'],  # Top Secret
}

def scan_content(text):
    detected = []
    for category, keywords in SENSITIVE_KEYWORDS.items():
        for kw in keywords:
            if kw in text.lower():
                detected.append((category, kw))
    return detected
```

Classification mapping:
- Detect 'nuclear' or similar → Top Secret
- Detect 'intelligence' or 'finance_classified' → Secret
- Detect 'defense' or 'diplomacy' or 'high_personnel' → Confidential
- Otherwise → Unclassified

### Rule 3 — Applicant type

```python
def check_applicant_type(applicant):
    if applicant.is_foreign_government():
        return 'Confidential', 'Foreign government applicant'

    if applicant.is_military_entity():
        return 'Confidential', 'Military entity applicant'

    if applicant.type == 'high_official':
        return 'Confidential', 'High-ranking official applicant'

    return 'Unclassified', None
```

### Rule 4 — Aggregation rule

Sometimes multiple low-sensitivity items combined → higher sensitivity:

```python
def check_aggregation(case):
    """If case has multiple sensitive signals, escalate."""
    signals = []

    if case.has_large_value():  # > 100B VND
        signals.append('large_value')
    if case.has_critical_infrastructure():
        signals.append('critical_infra')
    if case.has_cross_border():
        signals.append('cross_border')
    if case.involves_multiple_provinces():
        signals.append('multi_province')

    if len(signals) >= 3:
        return 'Confidential', f'Aggregation of signals: {signals}'

    return 'Unclassified', None
```

### Rule 5 — Default

If no rule triggers → Unclassified.

## Combination logic

```python
def decide_classification(case, entities, content, applicant):
    results = []

    results.append(check_location_sensitivity(entities))
    results.append(check_content_keywords(content))
    results.append(check_applicant_type(applicant))
    results.append(check_aggregation(case))

    # Return highest classification from all rules
    ranking = {'Unclassified': 0, 'Confidential': 1, 'Secret': 2, 'Top Secret': 3}
    highest = max(results, key=lambda r: ranking[r[0]])

    return {
        'level': highest[0],
        'reasoning': highest[1],
        'all_rules_fired': [r for r in results if r[1] is not None]
    }
```

## Human review gate

**Never auto-classify above Confidential without human review.**

- Unclassified → auto, no review
- Confidential → auto, but notifies Security team
- Secret → **requires** human security officer review
- Top Secret → **requires** senior security officer review + justification

```python
def write_classification(case_id, decision):
    if decision['level'] in ['Secret', 'Top Secret']:
        # Don't auto-apply, flag for human review
        create_task(
            case_id=case_id,
            type='human_security_review',
            suggested_level=decision['level'],
            assignee=security_officer_user,
            reasoning=decision['reasoning']
        )
    else:
        # Auto-apply Confidential / Unclassified
        apply_classification(case_id, decision)
```

## Qwen3 reasoning integration

For ambiguous cases, `SecurityOfficer` agent uses Qwen3-Max to reason:

```python
async def security_officer_reasoning(case_context):
    prompt = f"""
    Bạn là sĩ quan bảo vệ bí mật nhà nước tại cơ quan nhà nước Việt Nam.
    Luật BVBMNN 2018 Điều 3 có 4 cấp độ: Unclassified, Confidential (Mật),
    Secret (Tối mật), Top Secret (Tuyệt mật).

    Phân tích case sau và đề xuất cấp mật phù hợp:

    Case: {case_context}

    Trả về JSON:
    {{
      "suggested_level": "Unclassified | Confidential | Secret | Top Secret",
      "reasoning": "explanation",
      "rules_fired": ["rule_1", "rule_2"],
      "needs_human_review": bool,
      "confidence": float
    }}
    """

    response = await qwen_max(prompt, temperature=0.1)
    return parse_classification(response)
```

Combined with rule-based checks — rules override LLM if they fire (safer).

## Example cases

### Example 1 — Anh Minh CPXD normal

```
Case: Cấp phép XD nhà xưởng 500m² tại KCN Mỹ Phước
Location: KCN Mỹ Phước, Bình Dương (not sensitive)
Content keywords: none
Applicant: SME business
Aggregation: no signals

Decision: Unclassified
Reasoning: Standard SME construction permit, no sensitive factors.
Auto-apply: yes
```

### Example 2 — CPXD near military zone

```
Case: Cấp phép XD nhà máy tại Long An
Location: 3km from military base (check against sensitive zones KG)
Content: standard
Applicant: manufacturing company

Decision: Confidential
Reasoning: Location within 5km of military installation (Long An military zone)
Auto-apply: yes, but notify security team
```

### Example 3 — ĐKKD with high-ranking person

```
Case: Đăng ký doanh nghiệp, representative = Nguyễn Văn X
Content: standard
Applicant: business
SecurityOfficer scans text: "Nguyễn Văn X" appears in Top Official list (hypothetical)

Decision: Confidential
Reasoning: Applicant representative is in list of officials requiring classified handling
Auto-apply: yes, notify security
```

### Example 4 — Defense project

```
Case: Cấp phép XD dự án công trình quốc phòng
Content: "quốc phòng", "cơ sở quân sự" keywords
Applicant: Bộ Quốc phòng

Decision: Secret (by keyword) + Confidential (by applicant) → max = Secret
Auto-apply: no, requires human security officer review
```

## Downgrade rules

Classification can also be downgraded:
- After 5 years (Confidential → Unclassified per NĐ)
- On formal declassification decision by authority
- Manual override by Senior Security Officer with justification

Automatic downgrade runs as a nightly batch job checking `Classification.decided_at + retention_years`.

## Audit

Every classification decision writes AuditEvent:

```python
await audit_log(
    actor='SecurityOfficer',
    action='classify',
    resource_label='Case',
    resource_id=case_id,
    result='applied',
    reason=decision['reasoning'],
    details={
        'level': decision['level'],
        'rules_fired': decision['rules_fired'],
        'auto': True,
        'requires_human_review': decision['needs_human_review']
    }
)
```

## Testing scenarios

- [ ] Normal case → Unclassified
- [ ] Case near sensitive zone → Confidential with reasoning
- [ ] Case with defense keyword → Confidential
- [ ] Case with aggregation → Confidential
- [ ] Case triggering Secret → escalates to human review (does not auto-apply)
- [ ] Downgrade after retention → works
- [ ] Manual override by senior → works with audit
- [ ] Qwen3 reasoning fallback for ambiguous → works

## Demo moment

In pitch Scene 7 (Security wow moment), show a case in KCN Mỹ Phước → SecurityOfficer applies Confidential classification with visible reasoning → unauthorized user tries to access → denied → audit log with full reasoning visible.
