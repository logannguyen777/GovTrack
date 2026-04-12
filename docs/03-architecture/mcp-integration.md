# MCP Integration — Model Context Protocol for Agentic Graph Tools

Qwen3 supports **MCP (Model Context Protocol)** natively — the 2026 standard for exposing tools to LLM agents. GovFlow uses MCP to expose graph operations + legal lookup tools in a structured, type-safe way.

## What is MCP?

**Model Context Protocol** is an open standard (Anthropic + adopted by Alibaba Qwen, OpenAI) for:
- Exposing **tools** (functions the agent can call)
- Exposing **resources** (data the agent can read)
- Exposing **prompts** (pre-built prompts for common tasks)

Think: OpenAPI for LLM agents.

**Why MCP over custom function calling:**
- Standard format → reusable across LLM vendors
- Structured schema → reduces hallucination
- Built-in permission layer (tools have allow/deny)
- Observable — every tool call logged

## GovFlow MCP server architecture

```
┌────────────────────────────────────────┐
│         Qwen3-Max Agent                 │
│  (Planner / Compliance / LegalLookup /  │
│   etc.)                                  │
└─────────────┬──────────────────────────┘
              │
              │ MCP protocol (JSON-RPC over stdio or HTTP)
              │
              ▼
┌────────────────────────────────────────┐
│      GovFlow MCP Server                 │
│                                          │
│   Tool registry                          │
│   ├── graph.query_template              │
│   ├── graph.query_ad_hoc                │
│   ├── graph.create_vertex               │
│   ├── graph.create_edge                 │
│   ├── law.vector_search                 │
│   ├── law.get_effective_article         │
│   ├── tthc.find_by_category             │
│   ├── org.find_authorized               │
│   ├── notify.push_citizen               │
│   └── audit.log                         │
│                                          │
│   Resource registry                      │
│   ├── case/{case_id}                    │
│   ├── kg/taxonomy                       │
│   └── profiles/agent/{agent_name}       │
└─────────────┬──────────────────────────┘
              │
              ▼
       Agent SDK Guard (Tier 1)
              │
              ▼
       GDB / Hologres / OSS
```

## Tool definitions (examples)

### `graph.query_template`

```python
@mcp_tool
async def graph_query_template(
    template_name: str,
    parameters: dict
) -> dict:
    """
    Execute a predefined Gremlin template query.

    Available templates:
    - case.find_missing_components
    - case.get_initial_metadata
    - law.get_effective_article
    - law.get_cross_references
    - org.find_authorized_for_tthc
    - tthc.list_common
    ... (~30 total)

    Parameters must match the template's expected schema.
    """
    # Validate template exists
    if template_name not in TEMPLATE_LIBRARY:
        raise MCPError(f"Unknown template: {template_name}")

    # Validate parameters
    template = TEMPLATE_LIBRARY[template_name]
    template.validate_params(parameters)

    # SDK Guard check (agent-scoped)
    guard = current_agent_guard()
    guard.check_template_read_scope(template)

    # Execute
    gremlin_query = template.render(parameters)
    results = await gdb.submit(gremlin_query, bindings=parameters)

    # Property mask
    masked = apply_property_mask(results, guard.agent_profile)

    # Audit log
    await audit_log(
        actor=current_agent_name(),
        action='template_query',
        resource=template_name,
        parameters=parameters,
        result='success'
    )

    return masked
```

**Schema (for LLM):**
```json
{
  "name": "graph.query_template",
  "description": "Execute a predefined graph query template",
  "parameters": {
    "type": "object",
    "properties": {
      "template_name": {
        "type": "string",
        "enum": ["case.find_missing_components", "law.get_effective_article", ...]
      },
      "parameters": {
        "type": "object",
        "description": "Parameters specific to the chosen template"
      }
    },
    "required": ["template_name", "parameters"]
  }
}
```

### `graph.query_ad_hoc` (with guardrails)

```python
@mcp_tool
async def graph_query_ad_hoc(
    gremlin: str,
    description: str
) -> dict:
    """
    Execute an ad-hoc Gremlin query.

    IMPORTANT: Template queries are preferred. Only use this when
    no template fits the need. The query will be parsed and
    validated against the agent's scope.
    """
    guard = current_agent_guard()

    # Parse Gremlin AST
    ast = parse_gremlin(gremlin)

    # Validate read/write scope
    guard.check_read(ast)
    guard.check_write(ast)

    # Execute
    results = await gdb.submit(gremlin)

    # Property mask
    masked = apply_property_mask(results, guard.agent_profile)

    await audit_log(
        actor=current_agent_name(),
        action='ad_hoc_query',
        description=description,
        query_hash=hash(gremlin),
        result='success'
    )

    return masked
```

### `law.vector_search`

```python
@mcp_tool
async def law_vector_search(
    query_text: str,
    top_k: int = 10,
    filter_status: str = "effective"
) -> list[dict]:
    """
    Semantic search over Vietnamese law corpus using Hologres Proxima.

    Returns top_k candidate articles ranked by semantic similarity.
    Filtered by agent's clearance cap automatically.
    """
    guard = current_agent_guard()

    # Embed query
    query_vec = await embed(query_text, model='qwen3-embedding-v3')

    # Hologres Proxima search with ABAC
    rows = await hologres.execute("""
        SELECT law_code, article_num, clause_num, point_label, text,
               classification, status, effective_date,
               pm_approx_inner_product(embedding, %s) AS score
        FROM law_chunks
        WHERE status = %s
          AND classification <= %s
        ORDER BY embedding <=> %s
        LIMIT %s
    """, [query_vec, filter_status, guard.agent_profile.clearance_cap, query_vec, top_k])

    return rows
```

### `law.get_effective_article`

```python
@mcp_tool
async def law_get_effective_article(
    law_code: str,
    article_num: int
) -> dict:
    """
    Given a law code and article number, traverse the amendment chain
    to get the current effective version of the article.
    """
    # Uses template internally
    return await graph_query_template(
        template_name="law.get_effective_article",
        parameters={"law_code": law_code, "num": article_num}
    )
```

### `audit.log`

```python
@mcp_tool
async def audit_log_tool(
    action: str,
    resource_type: str,
    resource_id: str,
    reason: str = None
) -> dict:
    """
    Write an audit event. Called automatically by tool wrappers,
    but agents can also call explicitly for reasoning audit.
    """
    event = {
        'actor': current_agent_name(),
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'reason': reason,
        'timestamp': now(),
        'trace_id': current_trace_id()
    }

    # Write to both GDB (AuditEvent vertex) and Hologres (flat table)
    await gdb.addV('AuditEvent', **event)
    await hologres.insert('audit_events_flat', event)

    return {"audit_id": event['id']}
```

## Resource definitions

### `case/{case_id}`

```python
@mcp_resource
async def case_resource(case_id: str) -> dict:
    """
    Get the current state of a case as a resource (read-only data).
    Subject to agent read scope + property masking.
    """
    guard = current_agent_guard()

    case_data = await gdb.submit(f"""
        g.V().has('Case', 'id', '{case_id}')
         .project('case', 'documents', 'gaps', 'summaries')
         .by(valueMap())
         .by(__.out('HAS_BUNDLE').out('CONTAINS').valueMap().fold())
         .by(__.out('HAS_GAP').valueMap().fold())
         .by(__.out('HAS_SUMMARY').valueMap().fold())
    """)

    masked = apply_property_mask(case_data, guard.agent_profile)
    return masked
```

## Prompt templates (MCP prompts)

MCP also exposes **prompts** — pre-built prompts that agents can reference.

### `compliance_reasoning_prompt`

```python
@mcp_prompt
def compliance_reasoning_prompt(
    tthc_name: str,
    bundle_description: str,
    required_components: list[str],
    cited_laws: list[dict]
) -> list[dict]:
    """
    Generate a chat message sequence for Compliance agent to reason
    about whether a bundle satisfies TTHC requirements.
    """
    return [
        {
            "role": "system",
            "content": f"""
            You are a Vietnamese legal compliance officer with 20 years experience.
            Analyze whether the submitted bundle satisfies the requirements of
            {tthc_name}. Reference Vietnamese laws precisely by clause/point.
            Output structured JSON with gaps and citations.
            """
        },
        {
            "role": "user",
            "content": f"""
            TTHC: {tthc_name}
            Required components: {required_components}
            Cited laws: {cited_laws}
            Bundle description: {bundle_description}

            Identify gaps and explain why each is a gap with legal citation.
            """
        }
    ]
```

## MCP server implementation sketch

```python
# mcp_server.py
from mcp.server import MCPServer
from mcp.types import Tool, Resource, Prompt

app = MCPServer(name="govflow")

# Register tools
app.register_tool(graph_query_template)
app.register_tool(graph_query_ad_hoc)
app.register_tool(law_vector_search)
app.register_tool(law_get_effective_article)
app.register_tool(audit_log_tool)
# ... more

# Register resources
app.register_resource("case", case_resource)
app.register_resource("kg/taxonomy", kg_taxonomy_resource)

# Register prompts
app.register_prompt("compliance_reasoning", compliance_reasoning_prompt)

# Serve over HTTP for agents
app.run_http(host='0.0.0.0', port=3000)
```

## Agent invocation

```python
# agents/compliance.py
from openai import OpenAI

client = OpenAI(
    api_key=os.environ['DASHSCOPE_API_KEY'],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

async def compliance_run(case_id: str):
    # Get agent profile for Compliance
    profile = load_profile('Compliance')

    # Set current agent context (for MCP server's guard)
    set_current_agent('Compliance', profile)

    # Discover MCP tools
    tools = await mcp_client.list_tools(
        filter_by_agent_scope=profile
    )

    # Initial prompt
    messages = [
        {"role": "system", "content": profile.system_prompt},
        {"role": "user", "content": f"Check compliance for case {case_id}"}
    ]

    # Loop with function calling
    while True:
        response = await client.chat.completions.create(
            model="qwen-max-latest",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            break  # Agent done reasoning

        # Execute each tool call via MCP
        for tc in msg.tool_calls:
            result = await mcp_client.call_tool(
                tc.function.name,
                json.loads(tc.function.arguments)
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result)
            })

    # Done — agent has written to graph through tool calls
    return await gdb.submit(
        f"g.V().has('Case','id','{case_id}').out('HAS_GAP').count()"
    )
```

## Why MCP is a big deal for pitch

1. **2026 standard** — Qwen3 has native MCP support (marketing claim of Qwen team)
2. **Type-safe agent** — reduces hallucination vs unstructured function calls
3. **Permission integrated** — MCP tools have allow/deny built-in
4. **Observability** — every tool call loggable
5. **Reusable** — MCP tools work across Qwen3, GPT, Claude (demonstrates vendor-neutrality)

**Pitch quote:**
> "GovFlow orchestrator expose graph tools qua Model Context Protocol, chuẩn mới của 2026 được Qwen3 hỗ trợ native. Mỗi agent discover MCP tools theo scope của nó, Qwen3 sinh tool calls type-safe, GovFlow MCP server apply 3-tier permission engine trước khi hit GDB. Đây là pattern cutting-edge mà không đội nào khác build kịp trong 6 ngày."

## Implementation notes

- **For hackathon:** can embed MCP server in FastAPI app (not separate process)
- **Tool discovery per agent:** filter tool list based on `AgentProfile.allowed_tools`
- **Testing:** MCP tools are functions — easy unit test
- **Monitoring:** every tool call emits metric → CloudMonitor

## Trade-offs

**Con:** MCP adds ceremony vs direct function calling
**Pro:** Structure + permission + audit in 1 layer

**Con:** Qwen3 MCP maturity still developing (2025)
**Pro:** Fallback to Qwen3 OpenAI-compatible function calling if MCP issues

We'll ship MCP for pitch-worthy claim, with graceful degradation to plain function calling if needed.
