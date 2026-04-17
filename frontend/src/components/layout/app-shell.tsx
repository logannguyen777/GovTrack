"use client";

import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { CommandPalette } from "./command-palette";
import { useArtifactPanelStore } from "@/lib/stores/artifact-panel-store";
import { AgentArtifactPanel } from "@/components/agents/agent-artifact-panel";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";

// ---------------------------------------------------------------------------
// Mobile breakpoint hook
// ---------------------------------------------------------------------------

function useIsMobile(breakpoint = 768): boolean {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    setIsMobile(mql.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [breakpoint]);

  return isMobile;
}

// ---------------------------------------------------------------------------
// AppShell
// ---------------------------------------------------------------------------
//
// Layout structure:
//   <aside>Sidebar</aside>
//   <div>
//     <header>TopBar</header>
//     <main>
//       <div>{children}</div>
//       [Desktop] <aside 420px>AgentArtifactPanel</aside>
//     </main>
//   </div>
//   [Mobile] <Sheet>AgentArtifactPanel</Sheet>
//   <CommandPalette />
// ---------------------------------------------------------------------------

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const isMobile = useIsMobile();
  // mounted guard: the artifact panel store uses persist middleware (localStorage).
  // Reading isOpen before mount causes React #418 because SSR always sees isOpen=false
  // while client may restore isOpen=true from localStorage.
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const { isOpen: isArtifactPanelOpen, caseId: artifactCaseId, close: closeArtifact } =
    useArtifactPanelStore();

  // Only use the persisted isOpen state after client mount to avoid hydration mismatch.
  const showArtifactPanel = mounted && isArtifactPanelOpen;

  // Register Cmd+K / Ctrl+K keyboard shortcut with cleanup
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setCommandOpen((prev) => !prev);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown]);

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ backgroundColor: "var(--bg-app)" }}
    >
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
      />

      {/* Main column: top bar + page content + optional right panel */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar onCommandOpen={() => setCommandOpen(true)} />

        <main className="flex flex-1 overflow-hidden">
          {/* Page content */}
          <div
            className="flex-1 overflow-auto"
            style={{ padding: "var(--space-6)" }}
            id="main-content"
            tabIndex={-1}
            aria-label="Nội dung chính"
          >
            {children}
          </div>

          {/* Desktop right panel — hidden on mobile */}
          {showArtifactPanel && !isMobile && (
            <aside
              className="w-[420px] shrink-0 overflow-hidden border-l hidden md:block"
              style={{ borderColor: "var(--border-subtle)" }}
              aria-label="Panel AI tiến trình"
            >
              <AgentArtifactPanel
                caseId={artifactCaseId}
                onClose={closeArtifact}
              />
            </aside>
          )}
        </main>
      </div>

      {/* Mobile sheet — renders as bottom/right overlay */}
      <Sheet
        open={showArtifactPanel && isMobile}
        onOpenChange={(open) => {
          if (!open) closeArtifact();
        }}
      >
        <SheetContent side="right" showCloseButton={false}>
          <AgentArtifactPanel
            caseId={artifactCaseId}
            onClose={closeArtifact}
          />
        </SheetContent>
      </Sheet>

      {/* Command palette — portal-rendered, no layout impact */}
      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}
