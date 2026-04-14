"use client";

import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { CommandPalette } from "./command-palette";

// ---------------------------------------------------------------------------
// AppShell
// ---------------------------------------------------------------------------
//
// Manages sidebar collapsed state and command palette open state.
// Registers a Cmd+K / Ctrl+K global keyboard shortcut with proper cleanup.
// Renders:
//   <aside>Sidebar</aside>
//   <div>
//     <header>TopBar</header>
//     <main>{children}</main>
//   </div>
//   <CommandPalette />
// ---------------------------------------------------------------------------

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

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

      {/* Main column: top bar + page content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar onCommandOpen={() => setCommandOpen(true)} />

        <main
          className="flex-1 overflow-auto"
          style={{ padding: "var(--space-6)" }}
          id="main-content"
          tabIndex={-1}
          aria-label="Nội dung chính"
        >
          {children}
        </main>
      </div>

      {/* Command palette — portal-rendered, no layout impact */}
      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}
