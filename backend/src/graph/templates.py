"""
backend/src/graph/templates.py
Gremlin Template Library -- 30 parameterized queries for agent tools.
Each template is a (query_string, description, parameter_names) tuple.
"""
from dataclasses import dataclass


@dataclass
class GremlinTemplate:
    name: str
    description: str
    query: str
    params: list[str]


TEMPLATES: dict[str, GremlinTemplate] = {}


def _register(name: str, description: str, query: str, params: list[str]) -> None:
    TEMPLATES[name] = GremlinTemplate(name=name, description=description, query=query, params=params)


# ---- 1. Lookup (4) ----
_register(
    "get_law_by_id",
    "Retrieve a Law vertex by _kg_id",
    "g.V().has('_kg_id', kg_id).valueMap(true)",
    ["kg_id"],
)

_register(
    "get_article",
    "Retrieve an Article by _kg_id",
    "g.V().has('_kg_id', kg_id).valueMap(true)",
    ["kg_id"],
)

_register(
    "get_tthc_spec",
    "Retrieve a TTHCSpec by tthc_code",
    "g.V().has('TTHCSpec', 'code', code).valueMap(true)",
    ["code"],
)

_register(
    "get_case",
    "Retrieve a Case vertex by case_id",
    "g.V().has('Case', 'case_id', case_id).valueMap(true)",
    ["case_id"],
)

# ---- 2. Traversal (8) ----
_register(
    "law_articles",
    "Get all articles contained in a law",
    "g.V().has('_kg_id', kg_id).out('CONTAINS').hasLabel('Article').valueMap(true)",
    ["kg_id"],
)

_register(
    "article_clauses",
    "Get all clauses in an article",
    "g.V().has('_kg_id', kg_id).out('HAS_CLAUSE').hasLabel('Clause').valueMap(true)",
    ["kg_id"],
)

_register(
    "tthc_required_components",
    "Get all required components for a TTHC",
    "g.V().has('TTHCSpec', 'code', code).out('REQUIRES').valueMap(true)",
    ["code"],
)

_register(
    "tthc_legal_basis",
    "Get legal articles governing a TTHC",
    "g.V().has('TTHCSpec', 'code', code).out('GOVERNED_BY').valueMap(true)",
    ["code"],
)

_register(
    "case_documents",
    "Get all documents in a case's bundles",
    "g.V().has('Case', 'case_id', case_id).out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document').valueMap(true)",
    ["case_id"],
)

_register(
    "case_gaps",
    "Get all identified gaps for a case",
    "g.V().has('Case', 'case_id', case_id).out('HAS_GAP').valueMap(true)",
    ["case_id"],
)

_register(
    "case_opinions",
    "Get all agent opinions for a case",
    "g.V().has('Case', 'case_id', case_id).out('HAS_OPINION').valueMap(true)",
    ["case_id"],
)

_register(
    "case_agent_steps",
    "Get all agent processing steps for a case (ordered by time)",
    "g.V().has('Case', 'case_id', case_id).out('PROCESSED_BY').valueMap(true)",
    ["case_id"],
)

# ---- 3. Subgraph (2) ----
_register(
    "case_subgraph",
    "Get full case subgraph (1-hop neighborhood)",
    "g.V().has('Case', 'case_id', case_id).bothE().bothV().path().by(valueMap(true)).by(label)",
    ["case_id"],
)

_register(
    "org_hierarchy",
    "Get organization hierarchy from a root org",
    "g.V().has('Organization', 'org_id', org_id).repeat(out('PARENT_OF')).until(outE('PARENT_OF').count().is(0)).path().by(valueMap(true))",
    ["org_id"],
)

# ---- 4. Amendment chain (2) ----
_register(
    "amendment_chain",
    "Get the amendment chain for a law",
    "g.V().has('_kg_id', kg_id).repeat(out('AMENDED_BY')).until(outE('AMENDED_BY').count().is(0)).path().by(valueMap(true))",
    ["kg_id"],
)

_register(
    "supersession_chain",
    "Get the supersession chain for a law",
    "g.V().has('_kg_id', kg_id).repeat(out('SUPERSEDED_BY')).until(outE('SUPERSEDED_BY').count().is(0)).path().by(valueMap(true))",
    ["kg_id"],
)

# ---- 5. Cross-reference (2) ----
_register(
    "article_references",
    "Get articles referenced by a given article",
    "g.V().has('_kg_id', kg_id).out('REFERENCES').valueMap(true)",
    ["kg_id"],
)

_register(
    "citing_articles",
    "Get articles that reference a given article (reverse)",
    "g.V().has('_kg_id', kg_id).in('REFERENCES').valueMap(true)",
    ["kg_id"],
)

# ---- 6. Case processing (6) ----
_register(
    "create_case",
    "Create a new Case vertex with temporal tracking",
    "g.addV('Case').property('case_id', case_id).property('code', code).property('status', 'submitted').property('submitted_at', submitted_at).property('department_id', dept_id).property('tthc_code', tthc_code).property('valid_from', submitted_at)",
    ["case_id", "code", "submitted_at", "dept_id", "tthc_code"],
)

_register(
    "update_case_status",
    "Update the status of a Case with timestamp for temporal tracking",
    "g.V().has('Case', 'case_id', case_id).property('status', status).property('status_updated_at', updated_at)",
    ["case_id", "status", "updated_at"],
)

_register(
    "add_gap",
    "Add a Gap vertex linked to a Case with temporal tracking",
    "g.addV('Gap').property('gap_id', gap_id).property('description', desc).property('severity', severity).property('component_name', comp).property('valid_from', created_at).as('gap').V().has('Case', 'case_id', case_id).addE('HAS_GAP').to('gap')",
    ["gap_id", "desc", "severity", "comp", "case_id", "created_at"],
)

_register(
    "add_citation",
    "Add a Citation vertex with temporal tracking",
    "g.addV('Citation').property('citation_id', cit_id).property('law_ref', law_ref).property('article_ref', art_ref).property('relevance_score', score).property('snippet', snippet).property('valid_from', created_at)",
    ["cit_id", "law_ref", "art_ref", "score", "snippet", "created_at"],
)

_register(
    "add_opinion",
    "Add an Opinion from an agent to a Case with temporal tracking",
    "g.addV('Opinion').property('opinion_id', op_id).property('agent_name', agent).property('verdict', verdict).property('reasoning', reasoning).property('confidence', conf).property('valid_from', created_at).as('op').V().has('Case', 'case_id', case_id).addE('HAS_OPINION').to('op')",
    ["op_id", "agent", "verdict", "reasoning", "conf", "case_id", "created_at"],
)

_register(
    "add_agent_step",
    "Log an AgentStep vertex with temporal tracking",
    "g.addV('AgentStep').property('step_id', step_id).property('agent_name', agent).property('action', action).property('input_tokens', in_tok).property('output_tokens', out_tok).property('duration_ms', dur).property('valid_from', ts).as('step').V().has('Case', 'case_id', case_id).addE('PROCESSED_BY').to('step')",
    ["step_id", "agent", "action", "in_tok", "out_tok", "dur", "case_id", "ts"],
)

# ---- 7. Task DAG (4) ----
_register(
    "create_task",
    "Create a Task vertex for the agent DAG with temporal tracking",
    "g.addV('Task').property('task_id', task_id).property('name', name).property('status', 'pending').property('agent_name', agent).property('case_id', case_id).property('valid_from', created_at)",
    ["task_id", "name", "agent", "case_id", "created_at"],
)

_register(
    "add_task_dependency",
    "Create DEPENDS_ON edge between tasks",
    "g.V().has('Task', 'task_id', downstream).addE('DEPENDS_ON').to(g.V().has('Task', 'task_id', upstream))",
    ["downstream", "upstream"],
)

_register(
    "get_ready_tasks",
    "Get tasks that are pending and have all dependencies completed",
    "g.V().has('Task', 'case_id', case_id).has('status', 'pending').where(out('DEPENDS_ON').has('status', neq('completed')).count().is(0)).valueMap(true)",
    ["case_id"],
)

_register(
    "update_task_status",
    "Update a task's status with timestamp for temporal tracking",
    "g.V().has('Task', 'task_id', task_id).property('status', status).property('status_updated_at', updated_at)",
    ["task_id", "status", "updated_at"],
)

# ---- Document analysis (2) ----
_register(
    "update_document_properties",
    "Update Document vertex with analysis results from DocAnalyzer",
    "g.V().has('Document', 'doc_id', doc_id)"
    ".property('type', dtype).property('confidence', conf)"
    ".property('has_red_stamp', stamp).property('has_signature', sig)"
    ".property('format_valid', fmt).property('ocr_quality', quality)"
    ".property('needs_review', review)",
    ["doc_id", "dtype", "conf", "stamp", "sig", "fmt", "quality", "review"],
)

_register(
    "create_extracted_entity",
    "Create an ExtractedEntity vertex linked to a Document via EXTRACTED edge",
    "g.addV('ExtractedEntity')"
    ".property('entity_id', eid).property('field_name', fname)"
    ".property('value', val).property('confidence', conf)"
    ".property('page_num', pnum)"
    ".as('entity')"
    ".V().has('Document', 'doc_id', doc_id).addE('EXTRACTED').to('entity')",
    ["eid", "fname", "val", "conf", "pnum", "doc_id"],
)

# ---- 8. Audit (1) ----
_register(
    "add_audit_event",
    "Create an AuditEvent vertex",
    "g.addV('AuditEvent').property('event_type', ev_type).property('actor_id', actor).property('target_type', tgt_type).property('target_id', tgt_id).property('timestamp', ts).property('details', details)",
    ["ev_type", "actor", "tgt_type", "tgt_id", "ts", "details"],
)

# ---- 9. Classification support (2) ----
_register(
    "case_doc_types_summary",
    "Get document types and extracted entities for a case (used by Classifier)",
    "g.V().has('Case', 'case_id', case_id)"
    ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
    ".project('doc_id', 'type', 'confidence', 'entities')"
    ".by(values('doc_id'))"
    ".by(coalesce(values('type'), constant('unknown')))"
    ".by(coalesce(values('confidence'), constant(0.0)))"
    ".by(out('EXTRACTED').valueMap('field_name', 'value').fold())",
    ["case_id"],
)

_register(
    "tthc_list_all",
    "List all TTHCSpec vertices for classification grounding",
    "g.V().hasLabel('TTHCSpec').valueMap(true).limit(limit)",
    ["limit"],
)

# ---- 10. Search support (1) ----
_register(
    "find_tthc_by_department",
    "Find all TTHC specs for a department",
    "g.V().has('TTHCSpec', 'department', dept).valueMap(true)",
    ["dept"],
)

# ---- 11. Compliance support (4) ----
_register(
    "case_compliance_context",
    "Get case with matched TTHC code, documents, and extracted entities for compliance checking",
    "g.V().has('Case', 'case_id', case_id)"
    ".project('case', 'tthc', 'documents')"
    ".by(valueMap(true))"
    ".by(out('MATCHES_TTHC').valueMap(true).fold())"
    ".by(out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
    ".project('doc', 'entities')"
    ".by(valueMap(true))"
    ".by(out('EXTRACTED').valueMap('field_name', 'value').fold())"
    ".fold())",
    ["case_id"],
)

_register(
    "case_find_missing_components",
    "Find RequiredComponents not yet satisfied by any document in the case bundle",
    "g.V().has('Case', 'case_id', case_id)"
    ".out('MATCHES_TTHC').out('REQUIRES')"
    ".filter(inE('SATISFIES').count().is(0))"
    ".valueMap(true)",
    ["case_id"],
)

_register(
    "update_case_property",
    "Update a single property on a Case vertex",
    "g.V().has('Case', 'case_id', case_id).property(prop_key, prop_val)",
    ["case_id", "prop_key", "prop_val"],
)

_register(
    "link_gap_to_requirement",
    "Create a GAP_FOR edge from a Gap to a RequiredComponent",
    "g.V().has('gap_id', gap_id).addE('GAP_FOR').to(g.V().has('_kg_id', req_id))",
    ["gap_id", "req_id"],
)


# ---- 12. Router support (4) ----
_register(
    "find_authorized_orgs",
    "Find organizations authorized for a TTHC code via AUTHORIZED_FOR edge",
    "g.V().has('TTHCSpec', 'code', code).out('AUTHORIZED_FOR').hasLabel('Organization').valueMap(true)",
    ["code"],
)

_register(
    "find_positions_in_dept",
    "Get positions in an organization sorted by workload (ascending)",
    "g.V().has('Organization', 'org_id', org_id)"
    ".in('BELONGS_TO').hasLabel('Position')"
    ".order().by(coalesce(values('current_workload'), constant(999)), asc)"
    ".valueMap(true)",
    ["org_id"],
)

_register(
    "assign_case_to_dept",
    "Write ASSIGNED_TO edge from Case to Organization with timestamp and actor",
    "g.V().has('Case', 'case_id', cid)"
    ".addE('ASSIGNED_TO')"
    ".to(g.V().has('Organization', 'org_id', oid))"
    ".property('assigned_at', ts).property('assigned_by', agent)",
    ["cid", "oid", "ts", "agent"],
)

_register(
    "case_gap_count",
    "Count gaps for a case",
    "g.V().has('Case', 'case_id', cid).out('HAS_GAP').count()",
    ["cid"],
)


# ---- 13. Consult support (7) ----
_register(
    "case_consult_targets",
    "Get organizations that need to be consulted for a case (CONSULTED edges from Router)",
    "g.V().has('Case', 'case_id', cid)"
    ".outE('CONSULTED').as('e').inV().as('org')"
    ".select('e', 'org').by(valueMap()).by(valueMap(true))",
    ["cid"],
)

_register(
    "case_context_for_consult",
    "Get case context for consult drafting: case properties, gaps, and citations",
    "g.V().has('Case', 'case_id', cid)"
    ".project('case', 'gaps', 'citations')"
    ".by(valueMap(true))"
    ".by(out('HAS_GAP').valueMap(true).fold())"
    ".by(out('HAS_GAP').out('CITES').valueMap(true).fold())",
    ["cid"],
)

_register(
    "create_consult_request",
    "Create a ConsultRequest vertex linked to Case via HAS_CONSULT_REQUEST",
    "g.addV('ConsultRequest')"
    ".property('request_id', req_id).property('case_id', cid)"
    ".property('target_org_id', org_id).property('target_org_name', org_name)"
    ".property('context_summary', ctx).property('main_question', mq)"
    ".property('sub_questions', sq).property('deadline', dl)"
    ".property('urgency', urg).property('status', 'pending')"
    ".property('created_at', ts)"
    ".as('cr')"
    ".V().has('Case', 'case_id', cid).addE('HAS_CONSULT_REQUEST').to('cr')",
    ["req_id", "cid", "org_id", "org_name", "ctx", "mq", "sq", "dl", "urg", "ts"],
)

_register(
    "get_consult_request",
    "Get a ConsultRequest vertex by request_id",
    "g.V().has('ConsultRequest', 'request_id', req_id).valueMap(true)",
    ["req_id"],
)

_register(
    "consult_request_opinions",
    "Get all opinions for a consult request",
    "g.V().has('ConsultRequest', 'request_id', req_id).out('HAS_OPINION').valueMap(true)",
    ["req_id"],
)

_register(
    "add_consult_opinion",
    "Add an Opinion vertex linked to a ConsultRequest via HAS_OPINION",
    "g.addV('Opinion')"
    ".property('opinion_id', op_id).property('agent_name', agent)"
    ".property('verdict', verdict).property('reasoning', reasoning)"
    ".property('confidence', conf).property('consensus', consensus)"
    ".property('recommendation', rec).property('opinion_count', cnt)"
    ".property('aggregated', agg).property('created_at', ts)"
    ".as('op')"
    ".V().has('ConsultRequest', 'request_id', req_id).addE('HAS_OPINION').to('op')",
    ["op_id", "agent", "verdict", "reasoning", "conf", "consensus", "rec", "cnt", "agg", "ts", "req_id"],
)

_register(
    "update_consult_request_status",
    "Update the status of a ConsultRequest vertex",
    "g.V().has('ConsultRequest', 'request_id', req_id).property('status', status)",
    ["req_id", "status"],
)

# ---- 14. Summary support (2) ----
_register(
    "add_summary",
    "Create a Summary vertex linked to a Case via HAS_SUMMARY edge",
    "g.addV('Summary')"
    ".property('summary_id', sid).property('text', text)"
    ".property('mode', mode).property('word_count', wc)"
    ".property('case_id', cid).property('clearance', cl)"
    ".property('created_at', ts)"
    ".as('sum')"
    ".V().has('Case', 'case_id', cid).addE('HAS_SUMMARY').to('sum')",
    ["sid", "text", "mode", "wc", "cid", "cl", "ts"],
)

_register(
    "case_existing_summaries",
    "Get existing summary modes for a case (idempotency check)",
    "g.V().has('Case', 'case_id', cid).out('HAS_SUMMARY').values('mode')",
    ["cid"],
)


# ---- 15. Drafter support (5) ----
_register(
    "case_decision",
    "Get the decision vertex for a case",
    "g.V().has('Case', 'case_id', cid).out('HAS_DECISION').valueMap(true)",
    ["cid"],
)

_register(
    "case_summaries_text",
    "Get all summary vertices for a case",
    "g.V().has('Case', 'case_id', cid).out('HAS_SUMMARY').valueMap(true)",
    ["cid"],
)

_register(
    "case_citations_via_gaps",
    "Get all citations reachable from a case via gaps",
    "g.V().has('Case', 'case_id', cid).out('HAS_GAP').out('CITES').valueMap(true)",
    ["cid"],
)

_register(
    "case_existing_drafts",
    "Get existing drafts for a case (idempotency check)",
    "g.V().has('Case', 'case_id', cid).out('HAS_DRAFT').valueMap(true)",
    ["cid"],
)

_register(
    "add_draft",
    "Create a Draft vertex linked to a Case via HAS_DRAFT edge",
    "g.addV('Draft')"
    ".property('draft_id', did).property('content_markdown', content)"
    ".property('doc_type', dtype).property('decision_type', dec_type)"
    ".property('validation_valid', vv).property('validation_issues', vi)"
    ".property('citizen_explanation', cit_exp)"
    ".property('status', 'draft').property('case_id', cid)"
    ".property('created_at', ts)"
    ".as('draft')"
    ".V().has('Case', 'case_id', cid).addE('HAS_DRAFT').to('draft')",
    ["did", "content", "dtype", "dec_type", "vv", "vi", "cit_exp", "cid", "ts"],
)


# ---- 16. SecurityOfficer support (4) ----
_register(
    "case_full_context",
    "Get full case with applicant, documents, entities, and classification (unrestricted)",
    "g.V().has('Case', 'case_id', case_id)"
    ".project('case', 'applicant', 'documents', 'classification')"
    ".by(valueMap(true))"
    ".by(out('SUBMITTED_BY').valueMap(true).fold())"
    ".by(out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
    ".project('doc', 'entities')"
    ".by(valueMap(true))"
    ".by(out('EXTRACTED').valueMap('field_name', 'value').fold())"
    ".fold())"
    ".by(coalesce(out('CLASSIFIED_AS').valueMap(true).fold(), constant([])))",
    ["case_id"],
)

_register(
    "case_current_classification",
    "Get current_classification property of a Case",
    "g.V().has('Case', 'case_id', case_id)"
    ".project('classification', 'case_id')"
    ".by(coalesce(values('current_classification'), constant('Unclassified')))"
    ".by(values('case_id'))",
    ["case_id"],
)

_register(
    "create_classification",
    "Create a Classification vertex linked to a Case via CLASSIFIED_AS edge",
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
    ["cls_id", "level", "reasoning", "keywords", "loc_sens", "agg_risk", "decided_by", "case_id", "ts"],
)

_register(
    "case_applicant_data",
    "Get Applicant data linked to a Case for aggregation risk check",
    "g.V().has('Case', 'case_id', case_id).out('SUBMITTED_BY').hasLabel('Applicant').valueMap(true)",
    ["case_id"],
)


def get_template(name: str) -> GremlinTemplate:
    """Get a template by name. Raises KeyError if not found."""
    return TEMPLATES[name]


def list_templates() -> list[dict]:
    """List all templates as dicts (for MCP tool registration)."""
    return [
        {"name": t.name, "description": t.description, "params": t.params}
        for t in TEMPLATES.values()
    ]
