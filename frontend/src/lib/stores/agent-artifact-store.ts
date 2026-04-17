import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ThinkingDelta = {
  agentId: string;
  agentName: string;
  text: string;
  updatedAt: string;
};

export type ToolCall = {
  id: string;
  agentId: string;
  agentName: string;
  name: string;
  args?: Record<string, unknown>;
  status: "pending" | "success" | "error";
  startedAt: string;
  finishedAt?: string;
  durationMs?: number;
  result?: unknown;
  error?: string;
};

export type SearchLog = {
  id: string;
  agentId: string;
  query: string;
  topK: Array<{ chunkId: string; article: string; similarity: number; preview: string }>;
  reranked?: Array<{ chunkId: string; score: number }>;
  citationsKept: string[];
};

export type GraphOp = {
  id: string;
  agentId: string;
  query: string;
  nodes: Array<{ id: string; label: string; type: string }>;
  edges: Array<{ source: string; target: string; label: string }>;
};

export type AgentBlock = {
  id: string; // "agentName:startTime"
  name: string;
  status: "running" | "completed" | "failed";
  startedAt: string;
  finishedAt?: string;
};

// ---------------------------------------------------------------------------
// Per-case artifact bucket
// ---------------------------------------------------------------------------

interface CaseArtifacts {
  activeAgents: AgentBlock[];
  thinking: Record<string, ThinkingDelta>; // keyed by agentId
  toolCalls: ToolCall[];
  searches: SearchLog[];
  graphOps: GraphOp[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_LIST_ENTRIES = 500;
const MAX_THINKING_BYTES = 50_000; // 50KB per agent

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

interface AgentArtifactState {
  byCaseId: Record<string, CaseArtifacts>;
  ingestEvent: (caseId: string, event: { type: string; data: unknown }) => void;
  hydrate: (caseId: string, snapshot: Partial<CaseArtifacts>) => void;
  reset: (caseId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function emptyBucket(): CaseArtifacts {
  return {
    activeAgents: [],
    thinking: {},
    toolCalls: [],
    searches: [],
    graphOps: [],
  };
}

function capList<T>(arr: T[]): T[] {
  return arr.length > MAX_LIST_ENTRIES ? arr.slice(arr.length - MAX_LIST_ENTRIES) : arr;
}

function capThinking(existing: string, delta: string): string {
  const combined = existing + delta;
  if (combined.length > MAX_THINKING_BYTES) {
    return combined.slice(combined.length - MAX_THINKING_BYTES);
  }
  return combined;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAgentArtifactStore = create<AgentArtifactState>((set) => ({
  byCaseId: {},

  ingestEvent: (caseId, event) => {
    set((state) => {
      const bucket: CaseArtifacts = state.byCaseId[caseId]
        ? { ...state.byCaseId[caseId] }
        : emptyBucket();

      const { type, data } = event;
      const d = data as Record<string, unknown>;

      switch (type) {
        case "agent_started": {
          const block: AgentBlock = {
            id: `${d.agent_name as string}:${d.started_at as string}`,
            name: (d.agent_name as string) ?? "",
            status: "running",
            startedAt: (d.started_at as string) ?? new Date().toISOString(),
          };
          bucket.activeAgents = capList([...bucket.activeAgents, block]);
          break;
        }

        case "agent_completed": {
          bucket.activeAgents = bucket.activeAgents.map((a) =>
            a.name === (d.agent_name as string)
              ? { ...a, status: "completed", finishedAt: d.finished_at as string | undefined }
              : a,
          );
          break;
        }

        case "agent_failed": {
          bucket.activeAgents = bucket.activeAgents.map((a) =>
            a.name === (d.agent_name as string)
              ? { ...a, status: "failed", finishedAt: d.finished_at as string | undefined }
              : a,
          );
          break;
        }

        case "agent_thinking_chunk": {
          const agentId = (d.agent_id as string) ?? (d.agent_name as string) ?? "unknown";
          const agentName = (d.agent_name as string) ?? agentId;
          const delta = (d.text ?? d.delta ?? "") as string;
          const existing = bucket.thinking[agentId];
          bucket.thinking = {
            ...bucket.thinking,
            [agentId]: {
              agentId,
              agentName,
              text: capThinking(existing?.text ?? "", delta),
              updatedAt: new Date().toISOString(),
            },
          };
          break;
        }

        case "agent_tool_call_start": {
          const call: ToolCall = {
            id: (d.id as string) ?? (d.tool_call_id as string) ?? crypto.randomUUID(),
            agentId: (d.agent_id as string) ?? "",
            agentName: (d.agent_name as string) ?? "",
            name: (d.name as string) ?? (d.tool_name as string) ?? "",
            args: d.args as Record<string, unknown> | undefined,
            status: "pending",
            startedAt: (d.started_at as string) ?? new Date().toISOString(),
          };
          bucket.toolCalls = capList([...bucket.toolCalls, call]);
          break;
        }

        case "agent_tool_call_result":
        case "tool_executed": {
          const id = (d.id as string) ?? (d.tool_call_id as string);
          const isError = d.status === "error" || !!d.error;
          const now = new Date().toISOString();
          bucket.toolCalls = bucket.toolCalls.map((tc) => {
            if (tc.id !== id) return tc;
            const finishedAt = (d.finished_at as string) ?? now;
            const durationMs =
              (d.duration_ms as number | undefined) ??
              (finishedAt
                ? new Date(finishedAt).getTime() - new Date(tc.startedAt).getTime()
                : undefined);
            return {
              ...tc,
              status: isError ? "error" : "success",
              result: d.result,
              error: d.error as string | undefined,
              finishedAt,
              durationMs,
            };
          });
          break;
        }

        case "search_log": {
          const log: SearchLog = {
            id: (d.id as string) ?? crypto.randomUUID(),
            agentId: (d.agent_id as string) ?? "",
            query: (d.query as string) ?? "",
            topK: (d.top_k as SearchLog["topK"]) ?? [],
            reranked: d.reranked as SearchLog["reranked"],
            citationsKept: (d.citations_kept as string[]) ?? [],
          };
          bucket.searches = capList([...bucket.searches, log]);
          break;
        }

        case "graph_operation": {
          const op: GraphOp = {
            id: (d.id as string) ?? crypto.randomUUID(),
            agentId: (d.agent_id as string) ?? "",
            query: (d.query as string) ?? "",
            nodes: (d.nodes as GraphOp["nodes"]) ?? [],
            edges: (d.edges as GraphOp["edges"]) ?? [],
          };
          bucket.graphOps = capList([...bucket.graphOps, op]);
          break;
        }

        default:
          break;
      }

      return { byCaseId: { ...state.byCaseId, [caseId]: bucket } };
    });
  },

  hydrate: (caseId, snapshot) => {
    set((state) => ({
      byCaseId: {
        ...state.byCaseId,
        [caseId]: { ...emptyBucket(), ...snapshot },
      },
    }));
  },

  reset: (caseId) => {
    set((state) => {
      const next = { ...state.byCaseId };
      delete next[caseId];
      return { byCaseId: next };
    });
  },
}));
