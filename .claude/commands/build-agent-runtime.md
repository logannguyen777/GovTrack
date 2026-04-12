You are building GovFlow's agent runtime: base agent class, orchestrator, MCP server, and DashScope wrapper. Follow docs/implementation/04-agent-runtime.md as the detailed guide.

Task: $ARGUMENTS (default: full agent runtime)

## What You Build

The foundation for 10 AI agents: BaseAgent ABC, AgentRuntime orchestrator, MCP tool server, DashScope client wrapper, and 10 YAML permission profiles.

## Steps

1. **`backend/src/agents/qwen_client.py`** — DashScope wrapper:
   ```python
   from openai import AsyncOpenAI

   class QwenClient:
       def __init__(self, api_key: str):
           self.client = AsyncOpenAI(
               api_key=api_key,
               base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
           )
       async def chat(self, model: str, messages: list, tools: list = None) -> dict:
           # model: "qwen-max-latest" | "qwen-vl-max-latest"
           # Handle function calling loop
           # Track tokens (input/output)
           # Retry with exponential backoff on rate limits
           # Timeout: 30s per call
   ```

2. **`backend/src/agents/base.py`** — BaseAgent ABC:
   ```python
   class BaseAgent(ABC):
       name: str
       model: str  # "qwen-max-latest" or "qwen-vl-max-latest"
       system_prompt: str
       profile: AgentProfile

       @abstractmethod
       async def run(self, case_id: str) -> dict: ...

       async def call_llm_with_tools(self, messages, tools) -> dict:
           # Tool calling loop:
           # 1. Send messages + tools to Qwen
           # 2. If response has tool_calls -> execute each via MCP
           # 3. Append tool results to messages
           # 4. Repeat until no tool_calls or max iterations (10)
           # 5. Log AgentStep to GDB for each iteration
           # 6. Broadcast via WebSocket
   ```

3. **Agent profile system:**
   - `AgentProfile` dataclass: name, role, read_node_labels[], read_edge_types[], write_node_labels[], write_edge_types[], property_masks{}, clearance_cap, allowed_tools[]
   - YAML files in `backend/src/agents/profiles/` (one per agent: planner.yaml, doc_analyzer.yaml, etc.)
   - Profile loader: read YAML -> instantiate AgentProfile -> cache

4. **`backend/src/agents/orchestrator.py`** — DAG executor:
   ```python
   class AgentRuntime:
       async def run(self, case_id: str):
           # 1. Run Planner first -> writes Task vertices
           # 2. Loop: find ready tasks (no pending DEPENDS_ON)
           # 3. asyncio.gather for parallel tasks
           # 4. Dispatch each task to correct agent by Task.name
           # 5. Update Task.status (pending -> running -> completed/failed)
           # 6. Retry failed tasks (max 2, exponential backoff)
           # 7. Return final case state
   ```

5. **`backend/src/agents/mcp_server.py`** — MCP tool registry:
   - Register all 30 Gremlin templates as MCP tools
   - Register law.vector_search (calls Hologres Proxima)
   - Register audit.log_event
   - Tool filtering: only expose tools in agent's `profile.allowed_tools`
   - Every tool call goes through SDK Guard before execution
   - Every tool call writes AuditEvent

6. **Create 10 YAML profiles** in `backend/src/agents/profiles/`:
   Reference docs/03-architecture/agent-catalog.md permission table:
   - planner.yaml: read [Case, Bundle, TTHCSpec], write [Task], clearance Confidential
   - doc_analyzer.yaml: read [Bundle, Document], write [Document, ExtractedEntity], clearance Top Secret
   - classifier.yaml: read [Case, Document metadata, TTHCSpec], write [MATCHES_TTHC], clearance Confidential
   - compliance.yaml: read [Case, Document, Entity, TTHCSpec, Article], write [Gap, Citation], clearance Confidential
   - legal_lookup.yaml: read [Law, Article, Clause, Point], write [Citation], clearance Confidential
   - router.yaml: read [Case, Organization, Position], write [ASSIGNED_TO, CONSULTED], clearance Confidential
   - consult.yaml: read [Case summary, Gap, Citation], write [ConsultRequest, Opinion], clearance Confidential
   - summarizer.yaml: read [Case (masked), Documents (redacted)], write [Summary], clearance varies
   - drafter.yaml: read [Case, Decision, Template], write [Draft], clearance Confidential
   - security_officer.yaml: read [ALL], write [Classification, AuditEvent], clearance Top Secret

## Spec References
- docs/03-architecture/agent-catalog.md — 10 agent specs + permissions
- docs/03-architecture/mcp-integration.md — MCP server design
- docs/03-architecture/gremlin-template-library.md — 30 template queries

## Verification
```python
# Agent profile loads
profile = load_profile("planner")
assert "Case" in profile.read_node_labels
assert profile.clearance_cap == "Confidential"

# Orchestrator processes dummy DAG
runtime = AgentRuntime(case_id="test-001")
await runtime.run()  # Should complete without error

# MCP tools filtered by profile
tools = mcp.get_tools_for_agent("planner")
assert "case.get_initial_metadata" in [t.name for t in tools]

# DashScope returns completion
client = QwenClient(api_key=config.DASHSCOPE_API_KEY)
resp = await client.chat("qwen-max-latest", [{"role":"user","content":"test"}])
assert resp is not None
```
