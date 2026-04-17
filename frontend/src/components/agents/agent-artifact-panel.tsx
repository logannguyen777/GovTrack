"use client";

import * as React from "react";
import { useAgentArtifact } from "@/hooks/use-agent-artifact";
import { AgentArtifactHeader } from "./agent-artifact-header";
import { AgentArtifactEmpty } from "./agent-artifact-empty";
import { ThinkingTab } from "./tabs/thinking-tab";
import { ToolsTab } from "./tabs/tools-tab";
import { SearchTab } from "./tabs/search-tab";
import { GraphTab } from "./tabs/graph-tab";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

// ---------------------------------------------------------------------------
// AgentArtifactPanel
// ---------------------------------------------------------------------------

interface AgentArtifactPanelProps {
  caseId: string | null;
  onClose: () => void;
}

export function AgentArtifactPanel({ caseId, onClose }: AgentArtifactPanelProps) {
  const data = useAgentArtifact(caseId);
  const activeAgent = data.activeAgents.find((a) => a.status === "running");

  // Build set of currently-running agent IDs for ThinkingTab streaming
  const runningAgentIds = React.useMemo(
    () =>
      new Set(
        data.activeAgents
          .filter((a) => a.status === "running")
          .map((a) => a.id.split(":")[0]),
      ),
    [data.activeAgents],
  );

  if (!caseId) {
    return (
      <div
        className="h-full flex flex-col"
        style={{ backgroundColor: "var(--bg-surface)" }}
      >
        <AgentArtifactEmpty />
      </div>
    );
  }

  return (
    <div
      className="h-full flex flex-col"
      style={{ backgroundColor: "var(--bg-surface)" }}
    >
      {/* Sticky header */}
      <AgentArtifactHeader
        caseId={caseId}
        activeAgent={activeAgent}
        onClose={onClose}
      />

      {/* Tabs */}
      <Tabs defaultValue="thinking" className="flex-1 flex flex-col overflow-hidden min-h-0">
        <TabsList
          variant="line"
          className="w-full justify-start border-b rounded-none px-3 shrink-0 h-auto py-0 bg-transparent gap-0"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <TabsTrigger
            value="thinking"
            className="text-xs px-3 py-2 rounded-none border-b-2 border-transparent data-active:border-[var(--accent-primary)]"
          >
            Suy nghĩ
          </TabsTrigger>
          <TabsTrigger
            value="tools"
            className="text-xs px-3 py-2 rounded-none border-b-2 border-transparent data-active:border-[var(--accent-primary)]"
          >
            Công cụ ({data.toolCalls.length})
          </TabsTrigger>
          <TabsTrigger
            value="search"
            className="text-xs px-3 py-2 rounded-none border-b-2 border-transparent data-active:border-[var(--accent-primary)]"
          >
            Tra cứu ({data.searches.length})
          </TabsTrigger>
          <TabsTrigger
            value="graph"
            className="text-xs px-3 py-2 rounded-none border-b-2 border-transparent data-active:border-[var(--accent-primary)]"
          >
            Đồ thị ({data.graphOps.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="thinking" className="flex-1 overflow-hidden p-0 m-0">
          <ThinkingTab
            thinking={data.thinking}
            runningAgentIds={runningAgentIds}
          />
        </TabsContent>

        <TabsContent value="tools" className="flex-1 overflow-hidden p-0 m-0">
          <ToolsTab toolCalls={data.toolCalls} />
        </TabsContent>

        <TabsContent value="search" className="flex-1 overflow-hidden p-0 m-0">
          <SearchTab searches={data.searches} />
        </TabsContent>

        <TabsContent value="graph" className="flex-1 overflow-hidden p-0 m-0">
          <GraphTab ops={data.graphOps} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
