import { create } from "zustand";
import { persist } from "zustand/middleware";

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

interface OnboardingState {
  completedTours: string[];
  dismissedHints: string[];
  markTourDone: (id: string) => void;
  dismissHint: (id: string) => void;
  resetAll: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      completedTours: [],
      dismissedHints: [],

      markTourDone: (id) =>
        set((s) => ({
          completedTours: s.completedTours.includes(id)
            ? s.completedTours
            : [...s.completedTours, id],
        })),

      dismissHint: (id) =>
        set((s) => ({
          dismissedHints: s.dismissedHints.includes(id)
            ? s.dismissedHints
            : [...s.dismissedHints, id],
        })),

      resetAll: () => set({ completedTours: [], dismissedHints: [] }),
    }),
    {
      name: "govflow-onboarding",
    },
  ),
);
