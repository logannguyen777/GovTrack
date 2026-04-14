"""
Tier 2 fallback: RBAC simulation for TinkerGraph (free-tier / local dev).
Intercepts connection-level identity and applies same grants as cloud GDB.
"""

from ..models.schemas import AgentProfile


class RBACSimulator:
    """Simulates GDB native RBAC when running on TinkerGraph."""

    def __init__(self, profile: AgentProfile):
        self.profile = profile

    def check_execution_privilege(self, query: str, parsed) -> None:
        """
        Mirror what the cloud GDB GRANT statements enforce.
        On TinkerGraph this is the authoritative check.
        On cloud GDB this is a defense-in-depth redundancy.
        """
        # Write operations: check INSERT grants
        if parsed.is_mutating:
            for label in parsed.created_labels:
                if label not in self.profile.write_node_labels:
                    raise PermissionError(
                        f"RBAC: {self.profile.agent_id} lacks INSERT on {label}"
                    )
        # Read operations: check SELECT grants
        for label in parsed.accessed_labels:
            if label not in self.profile.read_node_labels:
                raise PermissionError(
                    f"RBAC: {self.profile.agent_id} lacks SELECT on {label}"
                )
