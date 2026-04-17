"""
Tier 1: Pre-execution Gremlin bytecode analysis.
Intercepts queries before they reach GDB. Parses traversal steps to extract
which labels, edge types, and properties the query touches, then compares
against the agent's permission profile.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models.schemas import AgentProfile


class SDKGuardViolation(Exception):
    """Raised when a query violates the agent's permission scope."""

    def __init__(self, agent_id: str, violation_type: str, detail: str):
        self.agent_id = agent_id
        self.violation_type = violation_type
        self.detail = detail
        super().__init__(f"[{agent_id}] {violation_type}: {detail}")


@dataclass
class ParsedTraversal:
    """Result of parsing a Gremlin bytecode/query string."""

    accessed_labels: set[str] = field(default_factory=set)
    accessed_edge_types: set[str] = field(default_factory=set)
    accessed_properties: set[str] = field(default_factory=set)
    is_mutating: bool = False
    created_labels: set[str] = field(default_factory=set)
    created_edge_types: set[str] = field(default_factory=set)
    traversal_depth: int = 0


class SDKGuard:
    """Pre-execution permission gate for Gremlin queries."""

    # Gremlin step patterns for static analysis
    _LABEL_PATTERN = re.compile(r"\.hasLabel\(['\"](\w+)['\"]\)")
    _EDGE_PATTERN = re.compile(r"\.(outE|inE|bothE)\(['\"](\w+)['\"]\)")
    _PROPERTY_PATTERN = re.compile(r"\.values?\(['\"](\w+)['\"]\)")
    _MUTATE_PATTERN = re.compile(r"\.(addV|addE|property|drop)\(")
    _ADD_V_PATTERN = re.compile(r"\.addV\(['\"](\w+)['\"]\)")
    _ADD_E_PATTERN = re.compile(r"\.addE\(['\"](\w+)['\"]\)")
    _DEPTH_STEPS = re.compile(r"\.(out|in|both|outE|inE|bothE)\(")

    def __init__(self, profile: AgentProfile):
        self.profile = profile

    def parse_query(self, query: str) -> ParsedTraversal:
        """Extract labels, edges, properties, and mutation intent from query."""
        parsed = ParsedTraversal()
        parsed.accessed_labels = set(self._LABEL_PATTERN.findall(query))
        parsed.accessed_edge_types = {m[1] for m in self._EDGE_PATTERN.findall(query)}
        parsed.accessed_properties = set(self._PROPERTY_PATTERN.findall(query))
        parsed.is_mutating = bool(self._MUTATE_PATTERN.search(query))
        parsed.created_labels = set(self._ADD_V_PATTERN.findall(query))
        parsed.created_edge_types = set(self._ADD_E_PATTERN.findall(query))
        parsed.traversal_depth = len(self._DEPTH_STEPS.findall(query))
        return parsed

    def check_read(self, parsed: ParsedTraversal) -> None:
        """Verify agent can read all accessed labels and edges."""
        disallowed_labels = parsed.accessed_labels - set(self.profile.read_node_labels)
        if disallowed_labels:
            raise SDKGuardViolation(
                self.profile.agent_id,
                "READ_LABEL_DENIED",
                f"Cannot read labels: {disallowed_labels}",
            )
        disallowed_edges = parsed.accessed_edge_types - set(self.profile.read_edge_types)
        if disallowed_edges:
            raise SDKGuardViolation(
                self.profile.agent_id,
                "READ_EDGE_DENIED",
                f"Cannot traverse edges: {disallowed_edges}",
            )
        forbidden_accessed = parsed.accessed_properties & set(self.profile.forbidden_properties)
        if forbidden_accessed:
            raise SDKGuardViolation(
                self.profile.agent_id,
                "PROPERTY_FORBIDDEN",
                f"Cannot access properties: {forbidden_accessed}",
            )
        if parsed.traversal_depth > self.profile.max_traversal_depth:
            raise SDKGuardViolation(
                self.profile.agent_id,
                "DEPTH_EXCEEDED",
                f"Depth {parsed.traversal_depth} > max {self.profile.max_traversal_depth}",
            )

    def check_write(self, parsed: ParsedTraversal) -> None:
        """Verify agent can write all created labels and edges."""
        if not parsed.is_mutating:
            return
        disallowed_creates = parsed.created_labels - set(self.profile.write_node_labels)
        if disallowed_creates:
            raise SDKGuardViolation(
                self.profile.agent_id,
                "WRITE_LABEL_DENIED",
                f"Cannot create labels: {disallowed_creates}",
            )
        disallowed_edges = parsed.created_edge_types - set(self.profile.write_edge_types)
        if disallowed_edges:
            raise SDKGuardViolation(
                self.profile.agent_id,
                "WRITE_EDGE_DENIED",
                f"Cannot create edges: {disallowed_edges}",
            )

    def auto_rewrite(self, query: str) -> str:
        """Inject classification filter based on agent clearance cap."""
        cap = self.profile.clearance.value
        # Insert .has('classification', P.lte(cap)) after each hasLabel step
        rewritten = re.sub(
            r"(\.hasLabel\(['\"](\w+)['\"]\))",
            rf"\1.has('classification', P.lte({cap}))",
            query,
        )
        return rewritten

    # ------------------------------------------------------------------
    # Injection guard patterns
    # ------------------------------------------------------------------
    # Groovy line comment outside a string context
    _COMMENT_LINE = re.compile(r"//")
    # Groovy block comment
    _COMMENT_BLOCK = re.compile(r"/\*")
    # Control characters (ASCII 0-8, 11-31 except tab=9, lf=10, cr=13)
    _CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    # CR or LF anywhere inside the query body (normalised before parsing)
    _NEWLINE = re.compile(r"[\r\n]")
    # Top-level semicolons (multi-statement injection)
    _SEMICOLON = re.compile(r";")

    def _reject_if_injection(self, query: str) -> None:
        """Pre-reject queries containing injection markers.

        Checks (in order):
        1. Control characters (except normal whitespace already normalised).
        2. Groovy comment markers ``//`` or ``/*``.
        3. Newlines inside the query body.
        4. Semicolons at the top level (multi-statement).

        Raises SDKGuardViolation on any match.
        """
        if self._CONTROL_CHARS.search(query):
            raise SDKGuardViolation(
                self.profile.agent_id,
                "INJECTION_CONTROL_CHARS",
                "Query contains control characters",
            )
        if self._COMMENT_LINE.search(query):
            raise SDKGuardViolation(
                self.profile.agent_id,
                "INJECTION_COMMENT",
                "Query contains Groovy line comment marker '//'",
            )
        if self._COMMENT_BLOCK.search(query):
            raise SDKGuardViolation(
                self.profile.agent_id,
                "INJECTION_COMMENT",
                "Query contains Groovy block comment marker '/*'",
            )
        if self._NEWLINE.search(query):
            raise SDKGuardViolation(
                self.profile.agent_id,
                "INJECTION_NEWLINE",
                "Query contains CR or LF characters",
            )
        if self._SEMICOLON.search(query):
            raise SDKGuardViolation(
                self.profile.agent_id,
                "INJECTION_MULTI_STATEMENT",
                "Query contains semicolon (multi-statement injection rejected)",
            )

    def validate(self, query: str) -> str:
        """Full validation: inject_guard -> parse -> check_read -> check_write -> rewrite."""
        # Normalise leading/trailing whitespace before injection checks
        query = query.strip()
        self._reject_if_injection(query)
        parsed = self.parse_query(query)
        self.check_read(parsed)
        self.check_write(parsed)
        return self.auto_rewrite(query)
