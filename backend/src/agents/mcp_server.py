"""
backend/src/agents/mcp_server.py
MCP tool registry. Registers Gremlin templates and utility tools
as callable functions for agents. Filters tools per agent profile.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from ..auth import SYSTEM_SESSION
from ..database import oss_get_signed_url, oss_put_object, pg_connection
from ..graph.permitted_client import PermittedGremlinClient
from ..graph.sdk_guard import SDKGuard, SDKGuardViolation
from ..graph.templates import TEMPLATES, GremlinTemplate
from .profile import AgentProfile


async def _system_gdb_execute(query: str, bindings: dict | None = None) -> list:
    """Execute a Gremlin query using the SYSTEM_SESSION (MCP tool context)."""
    return await PermittedGremlinClient(SYSTEM_SESSION).execute(query, bindings or {})

logger = logging.getLogger("govflow.mcp")

# Binding value validation: allow alphanumeric, Vietnamese Unicode, common punctuation, UUIDs
_SAFE_BINDING_PATTERN = re.compile(
    r'^[\w\s\-.,;:!?@#/()\'"\[\]{}<>=+*&%$^|~`\u00C0-\u024F\u1E00-\u1EFF\u0300-\u036F]*$',
    re.UNICODE,
)
_MAX_BINDING_LENGTH = 10_000  # Max chars per binding value

# Allowlist for update_case_property's prop_key parameter
_SAFE_CASE_PROPERTIES = frozenset({
    "status", "urgency", "compliance_score", "compliance_status",
    "routing_note", "current_classification", "status_updated_at",
    "needs_human_review", "tthc_code", "tthc_name",
})


_TOOL_DESC_MAX_LENGTH = 200
_TOOL_DESC_FORBIDDEN_PATTERNS = [
    "ignore previous",
    "ignore above",
    "disregard",
    "system prompt",
    "you are now",
    "forget your instructions",
    "new instructions",
    "override",
]


def _validate_tool_description(name: str, description: str) -> str:
    """Validate and sanitize a tool description to prevent prompt injection.
    Locks descriptions at registration time so they cannot be tampered with."""
    if len(description) > _TOOL_DESC_MAX_LENGTH:
        logger.warning(f"Tool '{name}' description truncated from {len(description)} chars")
        description = description[:_TOOL_DESC_MAX_LENGTH]
    desc_lower = description.lower()
    for pattern in _TOOL_DESC_FORBIDDEN_PATTERNS:
        if pattern in desc_lower:
            logger.error(f"Tool '{name}' description contains forbidden pattern: '{pattern}'")
            raise ValueError(f"Tool description for '{name}' contains forbidden pattern: '{pattern}'")
    return description


class MCPToolRegistry:
    """
    Registry of callable tools.
    Each tool has a name, description, parameters (JSON Schema), and an execute function.
    Tool descriptions are validated at registration to prevent prompt injection.
    """

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        self._frozen = False  # Once frozen, no new tools can be registered
        self._register_gremlin_templates()
        self._register_utility_tools()
        self._frozen = True  # Lock registry after initialization

    def _register_tool(self, tool: MCPTool) -> None:
        """Register a single tool with validation. Raises if registry is frozen."""
        if self._frozen:
            raise RuntimeError(f"Cannot register tool '{tool.name}': registry is frozen")
        tool.description = _validate_tool_description(tool.name, tool.description)
        self._tools[tool.name] = tool

    def _register_gremlin_templates(self) -> None:
        """Register all 30 Gremlin templates as MCP tools."""
        for name, tmpl in TEMPLATES.items():
            self._register_tool(MCPTool(
                name=name,
                description=tmpl.description,
                parameters={
                    "type": "object",
                    "properties": {p: {"type": "string"} for p in tmpl.params},
                    "required": tmpl.params,
                },
                execute_fn=_make_gremlin_executor(tmpl),
            ))

    def _register_utility_tools(self) -> None:
        """Register non-Gremlin utility tools."""

        # Vector search over law chunks
        self._register_tool(MCPTool(
            name="law_vector_search",
            description="Search law chunks by semantic similarity using vector embeddings",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in Vietnamese"},
                    "top_k": {"type": "integer", "default": 10},
                    "law_id": {"type": "string", "description": "Optional: filter by law_id"},
                },
                "required": ["query"],
            },
            execute_fn=_execute_vector_search,
        ))

        # OSS upload
        self._register_tool(MCPTool(
            name="oss_upload",
            description="Upload content to object storage",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "OSS object key path"},
                    "content": {"type": "string", "description": "Content to upload (text)"},
                    "content_type": {"type": "string", "default": "text/plain"},
                },
                "required": ["key", "content"],
            },
            execute_fn=_execute_oss_upload,
        ))

        # OSS get signed URL
        self._register_tool(MCPTool(
            name="oss_get_url",
            description="Get a pre-signed download URL for an OSS object",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "OSS object key path"},
                },
                "required": ["key"],
            },
            execute_fn=_execute_oss_get_url,
        ))

        # Audit log
        self._register_tool(MCPTool(
            name="audit_log",
            description="Log an audit event to both GDB and Hologres",
            parameters={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "target_type": {"type": "string"},
                    "target_id": {"type": "string"},
                    "case_id": {"type": "string"},
                    "details": {"type": "string", "description": "JSON string of details"},
                },
                "required": ["event_type", "actor_id"],
            },
            execute_fn=_execute_audit_log,
        ))

    def get_tools_for_profile(self, profile: AgentProfile) -> list[dict]:
        """
        Return OpenAI-format tool definitions filtered by agent profile.
        Only tools listed in profile.allowed_tools are included.
        """
        tools = []
        for tool_name in profile.allowed_tools:
            if tool_name in self._tools:
                tool = self._tools[tool_name]
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                })
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        profile: AgentProfile,
    ) -> str:
        """
        Execute a tool call, respecting agent profile permissions.
        Returns the result as a JSON string.
        """
        # Permission check: is this tool in the agent's allowed list?
        if tool_name not in profile.allowed_tools:
            return json.dumps({
                "error": f"Tool '{tool_name}' not permitted for agent '{profile.name}'"
            })

        if tool_name not in self._tools:
            return json.dumps({"error": f"Tool '{tool_name}' not found"})

        tool = self._tools[tool_name]

        try:
            result = await tool.execute(arguments, profile=profile)
            # Apply property masking for Gremlin results
            if isinstance(result, list):
                result = _apply_property_masks(result, profile)
            return json.dumps(result, default=str, ensure_ascii=False)
        except SDKGuardViolation as e:
            logger.warning(f"Tool {tool_name} denied by SDKGuard: {e}")
            return json.dumps({"error": f"Permission denied: {e}"})
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return json.dumps({"error": str(e)})

    def list_all_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())


class MCPTool:
    """A single callable tool in the MCP registry."""

    def __init__(self, name: str, description: str, parameters: dict, execute_fn):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._execute_fn = execute_fn

    async def execute(self, arguments: dict, profile: AgentProfile | None = None) -> Any:
        """Execute the tool. Handles both sync and async executors.
        Passes profile to executors that support write permission checks."""
        import inspect
        sig = inspect.signature(self._execute_fn)
        if "profile" in sig.parameters:
            result = self._execute_fn(arguments, profile=profile)
        else:
            result = self._execute_fn(arguments)
        if asyncio.iscoroutine(result):
            return await result
        return result


# ============================================================
# Tool executor functions
# ============================================================

def _validate_binding_value(param_name: str, value: str, tool_name: str) -> str:
    """Validate a single Gremlin binding value against injection patterns."""
    value = str(value)
    if len(value) > _MAX_BINDING_LENGTH:
        raise ValueError(f"Binding '{param_name}' exceeds max length ({len(value)} > {_MAX_BINDING_LENGTH})")
    if not _SAFE_BINDING_PATTERN.match(value):
        logger.warning(f"[{tool_name}] Rejected unsafe binding '{param_name}': {value[:100]!r}")
        raise ValueError(f"Binding '{param_name}' contains disallowed characters")
    return value


def _make_gremlin_executor(tmpl: GremlinTemplate):
    """Create an async executor function for a Gremlin template.
    Validates binding values and enforces write permissions via SDKGuard."""
    async def executor(arguments: dict, profile: AgentProfile | None = None) -> list:
        # Validate binding values
        bindings = {}
        for p in tmpl.params:
            val = arguments.get(p, "")
            _validate_binding_value(p, val, tmpl.name)
            bindings[p] = val

        # Special validation: update_case_property only allows safe prop_keys
        if tmpl.name == "update_case_property":
            prop_key = bindings.get("prop_key", "")
            if prop_key not in _SAFE_CASE_PROPERTIES:
                raise ValueError(
                    f"Property '{prop_key}' not in allowed case properties: "
                    f"{sorted(_SAFE_CASE_PROPERTIES)}"
                )

        # Enforce write permissions via SDKGuard (Tier 1)
        if profile:
            perm_profile = profile.to_permission_profile()
            guard = SDKGuard(perm_profile)
            parsed = guard.parse_query(tmpl.query)
            if parsed.is_mutating:
                guard.check_write(parsed)  # Raises SDKGuardViolation if denied

        return await _system_gdb_execute(tmpl.query, bindings)
    return executor


async def _execute_vector_search(arguments: dict) -> list[dict]:
    """Execute vector similarity search over law_chunks."""
    from .qwen_client import QwenClient
    client = QwenClient()
    query = arguments["query"]
    top_k = int(arguments.get("top_k", 10))
    law_id = arguments.get("law_id")

    embeddings = await client.embed([query])
    query_vec = embeddings[0]
    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

    sql = """
        SELECT law_id, article_number, clause_path, content,
               1 - (embedding <=> $1::vector) as similarity
        FROM law_chunks
    """
    params: list = [vec_str]
    if law_id:
        sql += " WHERE law_id = $2"
        params.append(law_id)
    sql += f" ORDER BY embedding <=> $1::vector LIMIT ${len(params) + 1}"
    params.append(top_k)

    async with pg_connection() as conn:
        rows = await conn.fetch(sql, *params)

    return [
        {
            "law_id": r["law_id"],
            "article_number": r["article_number"],
            "clause_path": r["clause_path"],
            "content": r["content"],
            "similarity": float(r["similarity"]),
        }
        for r in rows
    ]


def _execute_oss_upload(arguments: dict) -> dict:
    """Upload text content to OSS."""
    key = arguments["key"]
    content = arguments["content"]
    content_type = arguments.get("content_type", "text/plain")
    oss_put_object(key, content.encode("utf-8"), content_type)
    return {"key": key, "status": "uploaded"}


def _execute_oss_get_url(arguments: dict) -> dict:
    """Get a pre-signed URL for an OSS object."""
    key = arguments["key"]
    url = oss_get_signed_url(key)
    return {"key": key, "signed_url": url}


async def _execute_audit_log(arguments: dict) -> dict:
    """Log an audit event to GDB and Hologres."""
    event_type = arguments["event_type"]
    actor_id = arguments.get("actor_id", "")
    target_type = arguments.get("target_type", "")
    target_id = arguments.get("target_id", "")
    case_id = arguments.get("case_id", "")
    details_str = arguments.get("details", "{}")

    now = datetime.now(UTC).isoformat()

    # GDB AuditEvent
    await _system_gdb_execute(
        "g.addV('AuditEvent')"
        ".property('event_type', et).property('actor_id', actor)"
        ".property('target_type', tt).property('target_id', tid)"
        ".property('timestamp', ts).property('details', det)",
        {"et": event_type, "actor": actor_id, "tt": target_type,
         "tid": target_id, "ts": now, "det": details_str},
    )

    # Hologres flat table
    async with pg_connection() as conn:
        await conn.execute(
            "INSERT INTO audit_events_flat (event_type, actor_id, actor_name, "
            "target_type, target_id, case_id, details) "
            "VALUES ($1, $2::uuid, $3, $4, $5, $6, $7::jsonb)",
            event_type, actor_id or None, "",
            target_type, target_id, case_id, details_str,
        )

    return {"status": "logged", "event_type": event_type}


def _apply_property_masks(results: list, profile: AgentProfile) -> list:
    """Remove masked properties from Gremlin query results."""
    if not profile.property_masks:
        return results

    masked = []
    for item in results:
        if isinstance(item, dict):
            label = item.get("label", "")
            masks = profile.property_masks.get(label, [])
            if masks:
                item = {k: v for k, v in item.items() if k not in masks}
        masked.append(item)
    return masked


# Global singleton
_registry: MCPToolRegistry | None = None


def get_mcp_registry() -> MCPToolRegistry:
    """Get or create the global MCP tool registry."""
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
    return _registry
