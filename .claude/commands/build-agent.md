You are implementing a specific GovFlow agent. The agent name is passed as $ARGUMENTS.

Valid agent names: planner, doc_analyzer, classifier, compliance, legal_lookup, router, consult, summarizer, drafter, security_officer

## Before You Start

1. Read the agent's implementation doc: `docs/implementation/{05-14}-agent-{name}.md`
2. Read the agent spec: `docs/03-architecture/agent-catalog.md`
3. Read the base class: `backend/src/agents/base.py`
4. Read the YAML profile: `backend/src/agents/profiles/{name}.yaml`

## What You Build

A single agent class at `backend/src/agents/{name}.py` that extends BaseAgent and implements the `async run(case_id)` method.

## Implementation Pattern

```python
from backend.src.agents.base import BaseAgent

class {AgentName}Agent(BaseAgent):
    name = "{agent_name}"
    model = "qwen-max-latest"  # or "qwen-vl-max-latest" for DocAnalyzer

    @property
    def system_prompt(self) -> str:
        return """Vietnamese system prompt for this agent's persona..."""

    async def run(self, case_id: str) -> dict:
        # 1. Read input from graph (via MCP tools)
        # 2. Process with LLM (call_llm_with_tools)
        # 3. Write output to graph (via MCP tools)
        # 4. Return result summary
        pass
```

## Per-Agent Details

- **planner**: Generate Task DAG. Tools: case.get_initial_metadata, tthc.list_common. Output: Task vertices + DEPENDS_ON edges.
- **doc_analyzer**: OCR via Qwen3-VL. Tools: custom OCR wrappers. Output: Document properties + ExtractedEntity vertices.
- **classifier**: Few-shot TTHC matching. Output: MATCHES_TTHC cross-graph edge. MUST match existing TTHCSpec vertex.
- **compliance**: Gap detection. Tools: case.find_missing_components. Calls LegalLookup for each gap. Output: Gap + Citation vertices.
- **legal_lookup**: 5-step Agentic GraphRAG (vector recall -> graph expansion -> rerank -> cross-ref -> cite). Output: Citation vertices.
- **router**: Rule-based + LLM disambiguation. Tools: org.find_authorized_for_tthc. Output: ASSIGNED_TO edge.
- **consult**: Auto-draft consult request. Output: ConsultRequest + Opinion vertices.
- **summarizer**: 3 modes (executive 3 lines, staff 10 lines, citizen plain). Output: 3 Summary vertices.
- **drafter**: ND 30/2020 compliant docs via Jinja2 templates. CANNOT publish (human gate). Output: Draft vertex.
- **security_officer**: Classification + access control. Full read access (Top Secret). Output: Classification + AuditEvent vertices.

## Conventions
- Vietnamese system prompts with diacritics
- All graph writes through PermittedGremlinClient (SDK Guard enforced)
- Every step logs AgentStep vertex + broadcasts via WebSocket
- Confidence thresholds: < threshold -> flag for human review
- Never hardcode TTHC codes or law references — query from KG

## After Implementation

1. Register agent in orchestrator dispatch map (`backend/src/agents/orchestrator.py`)
2. Verify YAML profile matches code's read/write patterns
3. Test with a sample case

## Verification
```python
agent = {AgentName}Agent(graph=gdb_client, mcp=mcp_server)
result = await agent.run("test-case-001")
# Verify expected vertices written to GDB
# Verify no SDK Guard violations for normal operations
# Verify AgentStep vertices created
```
