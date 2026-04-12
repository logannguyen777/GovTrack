# Gremlin Template Library — 30 prebuilt queries

**Why:** Gremlin is harder for LLM to generate than Cypher (fewer training examples). Template library lets Qwen3 pick template + fill parameters — 80% of queries avoid raw Gremlin generation.

**Location:** `backend/graph/templates.py`

**Pattern:**
```python
TEMPLATES = {
    "template_name": {
        "description": "...",
        "required_params": ["...", "..."],
        "query": "g.V()...",  # Python f-string or format template
        "read_labels": ["Case", "TTHCSpec"],
        "write_labels": [],
        "expected_output_schema": {...}
    }
}
```

---

## Case lifecycle templates (10)

### `case.create`
```groovy
g.addV('Case')
 .property('id', '${case_id}')
 .property('status', 'intake')
 .property('created_at', '${created_at}')
 .property('urgency', 'normal')
 .property('current_classification', 'Unclassified')
```

### `case.get_initial_metadata`
```groovy
g.V().has('Case', 'id', '${case_id}')
 .project('case', 'applicant', 'bundle_size', 'doc_count')
 .by(valueMap())
 .by(__.out('SUBMITTED_BY').valueMap())
 .by(__.out('HAS_BUNDLE').count())
 .by(__.out('HAS_BUNDLE').out('CONTAINS').count())
```

### `case.find_missing_components`
The core compliance check. Already shown in architecture docs.
```groovy
g.V().has('Case', 'id', '${case_id}')
 .out('MATCHES_TTHC').out('REQUIRES').as('req')
 .where(__.not(
    __.in('SATISFIES').out('EXTRACTED_FROM').in('CONTAINS').has('id', '${case_id}')
 ))
 .project('name', 'is_required', 'condition')
 .by('name')
 .by('is_required')
 .by('condition')
```

### `case.get_full_context`
```groovy
g.V().has('Case', 'id', '${case_id}')
 .project('case', 'documents', 'entities', 'gaps', 'citations', 'opinions', 'classification')
 .by(valueMap())
 .by(__.out('HAS_BUNDLE').out('CONTAINS').valueMap().fold())
 .by(__.out('HAS_BUNDLE').out('CONTAINS').out('EXTRACTED').valueMap().fold())
 .by(__.out('HAS_GAP').valueMap().fold())
 .by(__.out('HAS_GAP').out('HAS_CITATION').valueMap().fold())
 .by(__.out('HAS_OPINION').valueMap().fold())
 .by(__.out('CLASSIFIED_AS').valueMap().fold())
```

### `case.get_sla_status`
```groovy
g.V().has('Case', 'id', '${case_id}')
 .project('status', 'sla_deadline', 'days_elapsed', 'sla_remaining')
 .by('status')
 .by('sla_deadline')
 .by(__.values('created_at').math('(_)'))
 .by(__.values('sla_deadline').math('(_ - now())'))
```

### `case.list_active_by_dept`
```groovy
g.V().hasLabel('Case')
 .where(__.out('ASSIGNED_TO').has('Organization', 'id', '${dept_id}'))
 .has('status', P.within('processing', 'waiting_citizen', 'consulting'))
 .order().by('sla_deadline')
 .range(0, 50)
```

### `case.count_overdue_by_dept`
```groovy
g.V().hasLabel('Case')
 .where(__.out('ASSIGNED_TO').has('id', '${dept_id}'))
 .has('sla_deadline', P.lt('${now}'))
 .has('status', P.neq('published'))
 .count()
```

### `case.add_gap`
```groovy
g.V().has('Case', 'id', '${case_id}').as('c')
 .addV('Gap')
 .property('reason', '${reason}')
 .property('severity', '${severity}')
 .property('fix_suggestion', '${suggestion}')
 .as('g')
 .addE('HAS_GAP').from('c').to('g')
```

### `case.assign_to_dept`
```groovy
g.V().has('Case', 'id', '${case_id}').as('c')
 .V().has('Organization', 'id', '${dept_id}').as('d')
 .coalesce(
    __.inE('ASSIGNED_TO').where(__.outV().as('c')),
    __.addE('ASSIGNED_TO').from('c')
 )
 .property('assigned_at', '${now}')
 .property('assigned_by', '${user_id}')
```

### `case.update_status`
```groovy
g.V().has('Case', 'id', '${case_id}')
 .property('status', '${new_status}')
 .property('status_updated_at', '${now}')
```

---

## Law / TTHC templates (8)

### `law.get_effective_article`
```groovy
g.V().hasLabel('Article')
 .has('law_code', '${law_code}')
 .has('num', ${num})
 .until(__.not(__.out('SUPERSEDED_BY')))
 .repeat(__.out('SUPERSEDED_BY'))
 .valueMap('num', 'law_code', 'text', 'effective_date', 'classification')
```

### `law.get_cross_references`
```groovy
g.V().hasLabel('Article')
 .has('law_code', '${law_code}')
 .has('num', ${num})
 .out('REFERENCES')
 .dedup()
 .limit(${limit})
 .valueMap('num', 'law_code', 'text')
```

### `law.get_amendment_history`
```groovy
g.V().hasLabel('Article')
 .has('law_code', '${law_code}')
 .has('num', ${num})
 .emit()
 .repeat(__.out('AMENDED_BY'))
 .path()
 .by(valueMap('law_code', 'num', 'effective_date'))
```

### `tthc.find_by_category`
```groovy
g.V().hasLabel('TTHCSpec')
 .where(__.out('BELONGS_TO').has('ProcedureCategory', 'name', '${category_name}'))
 .valueMap('code', 'name', 'sla_days_law', 'authority_level')
```

### `tthc.list_common`
```groovy
g.V().hasLabel('TTHCSpec')
 .order().by('volume_per_year', decr)
 .limit(${limit})
 .valueMap('code', 'name', 'category')
```

### `tthc.get_spec_with_requirements`
```groovy
g.V().hasLabel('TTHCSpec').has('code', '${tthc_code}')
 .project('tthc', 'requirements', 'governing_laws')
 .by(valueMap())
 .by(__.out('REQUIRES').valueMap().fold())
 .by(__.out('GOVERNED_BY').valueMap('law_code', 'num', 'text').fold())
```

### `org.find_authorized_for_tthc`
```groovy
g.V().hasLabel('Organization')
 .where(__.out('AUTHORIZED_FOR').has('TTHCSpec', 'code', '${tthc_code}'))
 .where(__.values('scope_regions').is(P.containing('${region}')))
 .valueMap('id', 'name', 'level')
```

### `org.find_positions_in_dept`
```groovy
g.V().has('Organization', 'id', '${dept_id}')
 .in('BELONGS_TO')
 .hasLabel('Position')
 .order().by('current_workload', incr)
 .valueMap('id', 'title', 'current_workload')
```

---

## Agent trace + audit templates (6)

### `agent.log_step`
```groovy
g.addV('AgentStep')
 .property('agent_name', '${agent_name}')
 .property('tool_used', '${tool_used}')
 .property('input_json', '${input_json}')
 .property('output_json', '${output_json}')
 .property('latency_ms', ${latency_ms})
 .property('tokens_in', ${tokens_in})
 .property('tokens_out', ${tokens_out})
 .property('status', '${status}')
 .property('timestamp', '${now}')
 .as('step')
 .V().has('Case', 'id', '${case_id}')
 .addE('PROCESSED_BY').to('step')
```

### `agent.get_case_trace`
Replay reasoning trace of a case:
```groovy
g.V().has('Case', 'id', '${case_id}')
 .out('PROCESSED_BY')
 .order().by('timestamp')
 .valueMap('agent_name', 'tool_used', 'input_json', 'output_json', 'latency_ms', 'timestamp')
```

### `audit.log_event`
```groovy
g.addV('AuditEvent')
 .property('actor', '${actor}')
 .property('actor_type', '${actor_type}')
 .property('action', '${action}')
 .property('resource_label', '${resource_label}')
 .property('resource_id', '${resource_id}')
 .property('result', '${result}')
 .property('reason', '${reason}')
 .property('tier', '${tier}')
 .property('timestamp', '${now}')
```

### `audit.replay_case`
```groovy
g.V().has('Case', 'id', '${case_id}')
 .out('AUDITS')
 .order().by('timestamp')
 .valueMap('actor', 'action', 'resource_label', 'result', 'reason', 'timestamp')
```

### `audit.find_denials_by_user`
```groovy
g.V().hasLabel('AuditEvent')
 .has('actor', '${user_id}')
 .has('result', 'deny')
 .has('timestamp', P.gte('${since}'))
 .order().by('timestamp', decr)
 .valueMap()
```

### `audit.count_denials_window`
```groovy
g.V().hasLabel('AuditEvent')
 .has('result', 'deny')
 .has('timestamp', P.between('${start}', '${end}'))
 .group().by('actor').by(count())
```

---

## Search + discovery templates (6)

### `search.related_cases_by_tthc`
```groovy
g.V().has('TTHCSpec', 'code', '${tthc_code}')
 .in('MATCHES_TTHC')
 .hasLabel('Case')
 .has('status', 'published')
 .has('created_at', P.gte('${since}'))
 .order().by('created_at', decr)
 .limit(10)
 .valueMap('id', 'created_at', 'classification')
```

### `search.precedent_similar_cases`
```groovy
g.V().has('Case', 'id', '${case_id}')
 .out('MATCHES_TTHC').as('tthc')
 .in('MATCHES_TTHC')
 .where(P.neq('${case_id}'))
 .where(__.out('HAS_DECISION').has('type', 'approve'))
 .order().by(__.values('compliance_score'), decr)
 .limit(5)
```

---

## Permission check templates

### `permission.check_user_can_access_case`
```groovy
g.V().has('User', 'id', '${user_id}').as('u')
 .V().has('Case', 'id', '${case_id}').as('c')
 .and(
   __.select('u').values('clearance_level').is(P.gte(__.select('c').values('current_classification'))),
   __.select('u').values('department_ids').is(P.containing(
     __.select('c').out('ASSIGNED_TO').values('id')
   ))
 )
 .count().is(1)
```

---

## Template metadata schema

```python
@dataclass
class GremlinTemplate:
    name: str
    description: str
    required_params: list[str]
    optional_params: list[str]
    query_template: str  # uses ${param} substitution
    read_labels: list[str]
    write_labels: list[str]
    write_edge_types: list[str]
    expected_output_schema: dict
    sample_output: dict  # for testing + documentation

    def render(self, params: dict) -> str:
        # Validate params
        missing = set(self.required_params) - set(params.keys())
        if missing:
            raise ValueError(f"Missing params: {missing}")

        # Escape strings, validate types
        safe_params = escape_gremlin_params(params)
        return self.query_template.format(**safe_params)

    def validate_scope(self, agent_profile):
        # Check if this template requires labels beyond agent scope
        required_read = set(self.read_labels)
        allowed_read = set(agent_profile.read_node_labels)
        if not required_read.issubset(allowed_read):
            raise SDKGuardViolation(...)
```

## Why templates over raw Gremlin

| Aspect | Raw Gremlin | Templates |
|---|---|---|
| LLM accuracy | ~60% correct syntax | ~95% correct (just fill params) |
| Development speed | Slow (trial error) | Fast (pre-tested) |
| Security | Parse AST every time | Scope known at template definition |
| Debugging | Hard | Easy (known query) |
| Performance | Variable | Optimized at design time |

## Day-by-day build plan

- **Day 12/04:** 15 core templates (case.*, tthc.*, law.get_effective_article, agent.*, audit.*)
- **Day 13/04:** Remaining 15 (search.*, permission.*, org.*)
- **Day 14/04:** Test every template with real data in GDB
- **Day 15/04:** Agent integration — agents use templates instead of raw queries

## Testing

```python
# tests/test_templates.py
def test_case_find_missing():
    setup_test_case_with_gaps(['PCCC_approval'])
    result = execute_template(
        'case.find_missing_components',
        {'case_id': 'TEST-001'}
    )
    assert len(result) == 1
    assert result[0]['name'] == 'Văn bản thẩm duyệt PCCC'
```

Run tests against TinkerGraph in-memory for fast iteration, then against GDB for final validation.
