import { create } from "zustand";

// --- Trace Store: live agent steps ---
interface AgentStep {
  step_id: string;
  agent_name: string;
  action: string;
  status: "running" | "completed" | "failed";
  input_summary: string;
  output_summary: string;
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
  tokens_used?: number;
}

interface TraceStore {
  steps: AgentStep[];
  activeStepId: string | null;
  addStep: (step: AgentStep) => void;
  updateStep: (step_id: string, update: Partial<AgentStep>) => void;
  setActiveStep: (id: string | null) => void;
  reset: () => void;
}

export const useTraceStore = create<TraceStore>((set) => ({
  steps: [],
  activeStepId: null,
  addStep: (step) => set((s) => ({ steps: [...s.steps, step] })),
  updateStep: (step_id, update) =>
    set((s) => ({
      steps: s.steps.map((st) =>
        st.step_id === step_id ? { ...st, ...update } : st,
      ),
    })),
  setActiveStep: (id) => set({ activeStepId: id }),
  reset: () => set({ steps: [], activeStepId: null }),
}));

// --- Notification Store ---
interface Notification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

interface NotificationStore {
  notifications: Notification[];
  unreadCount: number;
  add: (n: Notification) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  unreadCount: 0,
  add: (n) =>
    set((s) => ({
      notifications: [n, ...s.notifications].slice(0, 100),
      unreadCount: s.unreadCount + 1,
    })),
  markRead: (id) =>
    set((s) => ({
      notifications: s.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n,
      ),
      unreadCount: Math.max(0, s.unreadCount - 1),
    })),
  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
}));
