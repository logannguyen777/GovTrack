import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ArtifactPanelState {
  caseId: string | null;
  isOpen: boolean;
  hasActivePipeline: boolean;
  setCase: (id: string | null) => void;
  toggle: () => void;
  open: () => void;
  close: () => void;
  setActivePipeline: (active: boolean) => void;
}

export const useArtifactPanelStore = create<ArtifactPanelState>()(
  persist(
    (set) => ({
      caseId: null,
      isOpen: false,
      hasActivePipeline: false,

      setCase: (id) => set({ caseId: id }),
      toggle: () => set((s) => ({ isOpen: !s.isOpen })),
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
      setActivePipeline: (active) => set({ hasActivePipeline: active }),
    }),
    {
      name: "govflow-artifact-panel",
      // Only persist isOpen — runtime state (caseId, hasActivePipeline) rehydrates from WS
      partialize: (state) => ({ isOpen: state.isOpen }),
    },
  ),
);
