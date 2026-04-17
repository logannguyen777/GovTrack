"use client";

/**
 * Judge mode — enables extra demo affordances when `?judge=1` is in the URL
 * or `localStorage["govflow-judge"] === "1"`.
 *
 * What it does:
 *  1. Persists the flag so navigating pages keeps the mode on.
 *  2. Exposes `useJudgeMode()` so any component can render architectural
 *     tooltips or pedagogic hints.
 *  3. Ships a floating "Làm mới demo" reset button (top-left) that calls
 *     `POST /api/demo/reset` — single-click restore of the 5 canonical cases
 *     without bouncing the process.
 *  4. Adds a subtle "Judge mode" pill in the top-right so the presenter sees
 *     the state at a glance.
 */

import * as React from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { RefreshCw, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface JudgeModeCtx {
  active: boolean;
  setActive: (on: boolean) => void;
}

const Ctx = React.createContext<JudgeModeCtx>({ active: false, setActive: () => {} });

export function useJudgeMode() {
  return React.useContext(Ctx);
}

/** Wrap a component with `data-judge-tip="..."` to surface a tooltip only
 *  when judge mode is active. This keeps pedagogic content out of normal flow.
 */
export function JudgeTip({ tip, children }: { tip: string; children: React.ReactNode }) {
  const { active } = useJudgeMode();
  if (!active) return <>{children}</>;
  return (
    <span className="relative group" data-judge-tip={tip}>
      {children}
      <span
        className="pointer-events-none absolute left-0 top-full z-50 mt-1 hidden whitespace-nowrap rounded-md border border-purple-300 bg-purple-50 px-2 py-1 text-[11px] font-medium text-purple-900 shadow-md group-hover:block dark:border-purple-700 dark:bg-purple-950 dark:text-purple-100"
      >
        <Sparkles className="mr-1 inline h-3 w-3" /> {tip}
      </span>
    </span>
  );
}

export function JudgeModeProvider({ children }: { children: React.ReactNode }) {
  const search = useSearchParams();
  const pathname = usePathname();
  const [active, setActive] = React.useState(false);
  const [resetting, setResetting] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const qFlag = search?.get("judge") === "1";
    const stored = window.localStorage.getItem("govflow-judge") === "1";
    if (qFlag && !stored) window.localStorage.setItem("govflow-judge", "1");
    setActive(qFlag || stored);
  }, [search, pathname]);

  const toggle = React.useCallback((on: boolean) => {
    setActive(on);
    if (typeof window !== "undefined") {
      if (on) window.localStorage.setItem("govflow-judge", "1");
      else window.localStorage.removeItem("govflow-judge");
    }
  }, []);

  async function handleReset() {
    if (resetting) return;
    setResetting(true);
    try {
      const token = typeof window !== "undefined" ? window.localStorage.getItem("govflow-token") : null;
      const res = await fetch("/api/demo/reset", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json().catch(() => ({}));
      toast.success(`Đã làm mới ${data.cases_created?.length ?? 0} hồ sơ mẫu`);
      // Soft refresh to reload current screen data
      if (typeof window !== "undefined") window.location.reload();
    } catch (err) {
      toast.error(
        err instanceof Error && err.message === "403"
          ? "Chỉ admin/an ninh được reset demo"
          : `Không reset được: ${err instanceof Error ? err.message : "unknown"}`,
      );
    } finally {
      setResetting(false);
    }
  }

  return (
    <Ctx.Provider value={{ active, setActive: toggle }}>
      {children}
      {active && (
        <>
          <button
            type="button"
            onClick={handleReset}
            disabled={resetting}
            className="fixed bottom-4 left-4 z-[60] flex items-center gap-2 rounded-full border border-purple-300 bg-purple-600 px-4 py-2 text-xs font-semibold text-white shadow-lg transition-all hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
            aria-label="Làm mới dữ liệu demo"
            title="POST /api/demo/reset — reseed 5 hồ sơ mẫu"
          >
            {resetting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Làm mới demo
          </button>
          <button
            type="button"
            onClick={() => toggle(false)}
            className="fixed bottom-4 left-44 z-[60] flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1.5 text-[11px] font-medium text-amber-800 shadow-md hover:bg-amber-100 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200"
            title="Tắt chế độ giám khảo"
          >
            <Sparkles className="h-3 w-3" /> Judge mode · Tắt
          </button>
        </>
      )}
    </Ctx.Provider>
  );
}
