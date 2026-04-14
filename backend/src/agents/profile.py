"""
backend/src/agents/profile.py
Agent profile definition and YAML loader.
Each agent has a profile that defines its permissions and capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass
class AgentProfile:
    """
    Defines an agent's identity and permission boundaries.
    Loaded from YAML files in backend/src/agents/profiles/.
    """
    name: str
    role: str                           # e.g. "intake_processor", "legal_analyst"
    model: str = "reasoning"            # model alias: reasoning | vision
    system_prompt: str = ""

    # GDB read permissions
    read_node_labels: list[str] = field(default_factory=list)
    read_edge_types: list[str] = field(default_factory=list)

    # GDB write permissions
    write_node_labels: list[str] = field(default_factory=list)
    write_edge_types: list[str] = field(default_factory=list)

    # Property-level masking (label -> list of hidden property keys)
    property_masks: dict[str, list[str]] = field(default_factory=dict)

    # Flat list of globally forbidden properties (used by SDK Guard)
    forbidden_properties: list[str] = field(default_factory=list)

    # Maximum classification level this agent can access
    clearance_cap: int = 1

    # Maximum graph traversal depth allowed
    max_traversal_depth: int = 5

    # MCP tools this agent is allowed to invoke
    allowed_tools: list[str] = field(default_factory=list)

    # Max iterations for the tool-calling loop
    max_iterations: int = 15

    # Max tokens budget per run
    max_tokens_budget: int = 50000

    def to_permission_profile(self):
        """Convert to pydantic AgentProfile used by the 3-tier permission engine."""
        from ..models.schemas import AgentProfile as PermProfile
        from ..models.enums import ClearanceLevel

        # Derive forbidden_properties from property_masks if not set explicitly
        forbidden = list(self.forbidden_properties)
        if not forbidden and self.property_masks:
            for props in self.property_masks.values():
                forbidden.extend(props)

        return PermProfile(
            agent_id=self.name,
            agent_name=self.name,
            clearance=ClearanceLevel(self.clearance_cap),
            read_node_labels=self.read_node_labels,
            write_node_labels=self.write_node_labels,
            read_edge_types=self.read_edge_types,
            write_edge_types=self.write_edge_types,
            forbidden_properties=forbidden,
            max_traversal_depth=self.max_traversal_depth,
        )


def load_profile(name: str) -> AgentProfile:
    """Load an agent profile from YAML."""
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Agent profile not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return AgentProfile(**data)


def load_all_profiles() -> dict[str, AgentProfile]:
    """Load all agent profiles from the profiles directory."""
    profiles = {}
    for path in PROFILES_DIR.glob("*.yaml"):
        name = path.stem
        profiles[name] = load_profile(name)
    return profiles
