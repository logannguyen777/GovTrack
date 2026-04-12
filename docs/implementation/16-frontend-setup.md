# 16 - Frontend Setup: Next.js 15, Design System, Auth, WebSocket

## Muc tieu (Objective)

Set up the Next.js 15 frontend project with the full design system (tokens, fonts,
dark/light mode), authentication layer, typed API client, WebSocket connection
manager, and base layout. After completing this guide, `npm run dev` serves a
working shell with sidebar navigation, mock login, and live WS connection.

---

## 1. Design Token System

### 1.1 CSS Custom Properties: `frontend/src/app/globals.css`

```css
@import "tailwindcss";

/* === GovFlow Design Tokens === */

@layer base {
  :root {
    /* --- Primitive palette (OKLCH) --- */
    --navy-950: oklch(0.15 0.03 250);    /* #0B1220 dark navy */
    --navy-900: oklch(0.20 0.03 250);
    --navy-800: oklch(0.28 0.03 250);
    --navy-700: oklch(0.35 0.03 250);
    --navy-600: oklch(0.42 0.02 250);
    --navy-500: oklch(0.50 0.02 250);
    --navy-400: oklch(0.60 0.02 250);
    --navy-300: oklch(0.70 0.015 250);
    --navy-200: oklch(0.82 0.01 250);
    --navy-100: oklch(0.92 0.005 250);
    --navy-50:  oklch(0.97 0.003 250);

    /* --- Classification colors --- */
    --classification-unclassified: oklch(0.70 0.17 160);  /* emerald */
    --classification-confidential: oklch(0.75 0.15 85);   /* amber */
    --classification-secret: oklch(0.70 0.18 55);         /* orange */
    --classification-top-secret: oklch(0.60 0.22 25);     /* red */

    /* --- Accent --- */
    --accent-primary: oklch(0.65 0.15 250);
    --accent-success: oklch(0.70 0.17 160);
    --accent-warning: oklch(0.75 0.15 85);
    --accent-error: oklch(0.60 0.22 25);
    --accent-info: oklch(0.65 0.12 250);

    /* --- Semantic (Light Mode) --- */
    --bg-app: var(--navy-50);
    --bg-surface: #ffffff;
    --bg-surface-raised: var(--navy-100);
    --bg-surface-overlay: rgba(255, 255, 255, 0.95);
    --text-primary: var(--navy-950);
    --text-secondary: var(--navy-600);
    --text-muted: var(--navy-400);
    --text-inverse: #ffffff;
    --border-subtle: var(--navy-200);
    --border-default: var(--navy-300);
    --border-strong: var(--navy-400);

    /* --- Spacing scale (4px base) --- */
    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
    --space-4: 1rem;
    --space-6: 1.5rem;
    --space-8: 2rem;
    --space-12: 3rem;
    --space-16: 4rem;

    /* --- Motion --- */
    --duration-micro: 150ms;
    --duration-default: 250ms;
    --duration-emphasis: 400ms;
    --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
    --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

    /* --- Typography --- */
    --font-ui: 'Inter', system-ui, sans-serif;
    --font-legal: 'Source Serif 4', Georgia, serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

    /* --- Radius --- */
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
    --radius-full: 9999px;

    /* --- Shadows --- */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
  }

  .dark {
    --bg-app: var(--navy-950);
    --bg-surface: var(--navy-900);
    --bg-surface-raised: var(--navy-800);
    --bg-surface-overlay: rgba(11, 18, 32, 0.95);
    --text-primary: var(--navy-50);
    --text-secondary: var(--navy-300);
    --text-muted: var(--navy-500);
    --text-inverse: var(--navy-950);
    --border-subtle: var(--navy-800);
    --border-default: var(--navy-700);
    --border-strong: var(--navy-600);
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
  }
}

/* === Font faces === */

body {
  font-family: var(--font-ui);
  background: var(--bg-app);
  color: var(--text-primary);
}

.font-legal { font-family: var(--font-legal); }
.font-mono  { font-family: var(--font-mono); }

/* === Classification badge utility classes === */

.badge-unclassified { background: var(--classification-unclassified); color: white; }
.badge-confidential { background: var(--classification-confidential); color: black; }
.badge-secret       { background: var(--classification-secret); color: white; }
.badge-top-secret   { background: var(--classification-top-secret); color: white; }
```

### 1.2 Font Loading: `frontend/src/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { AuthProvider } from "@/components/providers/auth-provider";

const inter = Inter({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter",
  display: "swap",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin", "vietnamese"],
  variable: "--font-source-serif",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GovFlow - Agentic TTHC Processing",
  description: "AI-powered Vietnamese administrative procedure processing",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={`${inter.variable} ${sourceSerif.variable} ${jetbrainsMono.variable}`}
    >
      <body className="antialiased">
        <ThemeProvider defaultTheme="dark" storageKey="govflow-theme">
          <QueryProvider>
            <AuthProvider>
              {children}
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

---

## 2. shadcn/ui Installation and Custom Components

### 2.1 Setup

```bash
cd /home/logan/GovTrack/frontend
npx shadcn@latest init
# Choose: TypeScript, Default style, CSS variables, src/components/ui
# Install base components:
npx shadcn@latest add button badge card dialog dropdown-menu \
  tabs toast tooltip select separator avatar input label \
  command sheet scroll-area popover
```

### 2.2 Custom Button Variants: `frontend/src/components/ui/button.tsx`

Extend the default button with GovFlow-specific variants:

```tsx
// Add to the buttonVariants cva definition:
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors duration-[var(--duration-default)] ease-[var(--ease-out-quart)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-[var(--accent-primary)] text-white hover:opacity-90",
        destructive: "bg-[var(--accent-error)] text-white hover:opacity-90",
        "destructive-confirm":
          "bg-[var(--accent-error)] text-white ring-2 ring-[var(--accent-error)]/30 hover:opacity-90",
        outline:
          "border border-[var(--border-default)] bg-transparent hover:bg-[var(--bg-surface-raised)]",
        secondary: "bg-[var(--bg-surface-raised)] text-[var(--text-primary)] hover:opacity-80",
        ghost: "hover:bg-[var(--bg-surface-raised)]",
        link: "text-[var(--accent-primary)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-6",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);
```

### 2.3 Classification Badge: `frontend/src/components/ui/classification-badge.tsx`

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const classificationBadgeVariants = cva(
  "inline-flex items-center rounded-sm px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest",
  {
    variants: {
      level: {
        unclassified: "bg-[var(--classification-unclassified)] text-white",
        confidential: "bg-[var(--classification-confidential)] text-black",
        secret: "bg-[var(--classification-secret)] text-white",
        "top-secret": "bg-[var(--classification-top-secret)] text-white animate-pulse",
      },
    },
    defaultVariants: { level: "unclassified" },
  }
);

interface ClassificationBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof classificationBadgeVariants> {}

export function ClassificationBadge({ level, className, ...props }: ClassificationBadgeProps) {
  const labels: Record<string, string> = {
    unclassified: "Unclassified",
    confidential: "Confidential",
    secret: "Secret",
    "top-secret": "Top Secret",
  };
  return (
    <span
      className={cn(classificationBadgeVariants({ level }), className)}
      role="status"
      aria-label={`Classification: ${labels[level ?? "unclassified"]}`}
      {...props}
    >
      {labels[level ?? "unclassified"]}
    </span>
  );
}
```

---

## 3. Dark/Light Mode Provider

### 3.1 File: `frontend/src/components/providers/theme-provider.tsx`

```tsx
"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light" | "system";

interface ThemeCtx {
  theme: Theme;
  setTheme: (t: Theme) => void;
  resolved: "dark" | "light";
}

const ThemeContext = createContext<ThemeCtx>({
  theme: "dark",
  setTheme: () => {},
  resolved: "dark",
});

export function ThemeProvider({
  children,
  defaultTheme = "dark",
  storageKey = "govflow-theme",
}: {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}) {
  const [theme, setThemeState] = useState<Theme>(defaultTheme);

  useEffect(() => {
    const stored = localStorage.getItem(storageKey) as Theme | null;
    if (stored) setThemeState(stored);
  }, [storageKey]);

  const resolved =
    theme === "system"
      ? (typeof window !== "undefined" &&
          window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light")
      : theme;

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolved === "dark");
  }, [resolved]);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    localStorage.setItem(storageKey, t);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolved }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
```

---

## 4. Base Layout: Sidebar + Top Bar + Command Palette

### 4.1 File: `frontend/src/components/layout/app-shell.tsx`

```tsx
"use client";

import { useState } from "react";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { CommandPalette } from "./command-palette";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

  // Cmd+K to open command palette
  if (typeof window !== "undefined") {
    window.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen(true);
      }
    });
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-app)]">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar onCommandOpen={() => setCommandOpen(true)} />
        <main className="flex-1 overflow-auto p-[var(--space-6)]">
          {children}
        </main>
      </div>
      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}
```

### 4.2 Sidebar navigation items:

```tsx
// frontend/src/components/layout/sidebar.tsx

const NAV_ITEMS = [
  { label: "Dashboard",   href: "/dashboard",   icon: "LayoutDashboard" },
  { label: "Intake",      href: "/intake",       icon: "Upload" },
  { label: "Cases",       href: "/inbox",        icon: "Inbox" },
  { label: "Compliance",  href: "/compliance",   icon: "ShieldCheck" },
  { label: "Documents",   href: "/documents",    icon: "FileText" },
  { label: "Trace",       href: "/trace",        icon: "GitBranch" },
  { label: "Security",    href: "/security",     icon: "Lock" },
] as const;

// Sidebar component renders:
// - GovFlow logo at top
// - NavItems with active state (left-border accent strip)
// - Collapse toggle button at bottom
// - Classification badge showing current session clearance
// - Width: 240px expanded, 64px collapsed
// - Transition: var(--duration-default) var(--ease-out-quart)
```

---

## 5. Authentication Layer

### 5.1 Auth Context: `frontend/src/components/providers/auth-provider.tsx`

```tsx
"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";

interface User {
  id: string;
  name: string;
  role: "citizen" | "staff_intake" | "staff_processor" | "leader" | "legal" | "security";
  clearance: 0 | 1 | 2 | 3;
  department?: string;
}

interface AuthCtx {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthCtx>({
  user: null, token: null,
  login: async () => {}, logout: () => {},
  isLoading: true,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("govflow-token");
    if (stored) {
      setToken(stored);
      fetchUser(stored).then(setUser).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error("Login failed");
    const { access_token, user: u } = await res.json();
    localStorage.setItem("govflow-token", access_token);
    setToken(access_token);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("govflow-token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

async function fetchUser(token: string): Promise<User> {
  const res = await fetch("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Session expired");
  return res.json();
}
```

### 5.2 Protected Route Middleware: `frontend/src/middleware.ts`

```tsx
import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/", "/auth/login", "/track"];
const INTERNAL_PREFIX = "/(internal)";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes: no auth required
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith("/api/public"))) {
    return NextResponse.next();
  }

  // Check JWT in cookie or Authorization header
  const token =
    request.cookies.get("govflow-token")?.value ||
    request.headers.get("Authorization")?.replace("Bearer ", "");

  if (!token) {
    const loginUrl = new URL("/auth/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

---

## 6. API Client with TanStack Query

### 6.1 Typed Fetch Wrapper: `frontend/src/lib/api.ts`

```tsx
type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`API ${status}: ${JSON.stringify(body)}`);
  }
}

async function api<T>(
  path: string,
  options: { method?: HttpMethod; body?: unknown; params?: Record<string, string> } = {}
): Promise<T> {
  const { method = "GET", body, params } = options;
  const token = typeof window !== "undefined" ? localStorage.getItem("govflow-token") : null;

  const url = new URL(path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));

  const res = await fetch(url.toString(), {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
  return res.json();
}

// Convenience methods
export const apiClient = {
  get: <T>(path: string, params?: Record<string, string>) =>
    api<T>(path, { params }),
  post: <T>(path: string, body: unknown) =>
    api<T>(path, { method: "POST", body }),
  put: <T>(path: string, body: unknown) =>
    api<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body: unknown) =>
    api<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) =>
    api<T>(path, { method: "DELETE" }),
};
```

### 6.2 TanStack Query Provider: `frontend/src/components/providers/query-provider.tsx`

```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,       // 30s before refetch
            retry: 2,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

---

## 7. WebSocket Client

### 7.1 Connection Manager: `frontend/src/lib/ws.ts`

```tsx
type Channel = "trace" | "notifications" | "audit";

interface WSMessage {
  channel: Channel;
  type: string;
  payload: unknown;
  timestamp: string;
}

class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private listeners = new Map<string, Set<(msg: WSMessage) => void>>();
  private url: string;

  constructor(baseUrl: string = "ws://localhost:8000/ws") {
    this.url = baseUrl;
  }

  connect(token: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(`${this.url}?token=${token}`);

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      const handlers = this.listeners.get(msg.channel);
      handlers?.forEach((h) => h(msg));
      // Also fire to wildcard listeners
      this.listeners.get("*")?.forEach((h) => h(msg));
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
        setTimeout(() => this.connect(token), delay);
      }
    };

    this.ws.onerror = (err) => {
      console.error("[WS] Error", err);
    };
  }

  subscribe(channel: Channel | "*", handler: (msg: WSMessage) => void): () => void {
    if (!this.listeners.has(channel)) this.listeners.set(channel, new Set());
    this.listeners.get(channel)!.add(handler);
    return () => this.listeners.get(channel)?.delete(handler);
  }

  send(channel: Channel, type: string, payload: unknown): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ channel, type, payload }));
  }

  disconnect(): void {
    this.maxReconnectAttempts = 0;
    this.ws?.close();
    this.ws = null;
  }
}

export const wsManager = new WebSocketManager();
```

### 7.2 Zustand Stores: `frontend/src/lib/store.ts`

```tsx
import { create } from "zustand";

// --- Trace Store: live agent steps ---
interface AgentStep {
  step_id: string;
  agent_id: string;
  agent_name: string;
  status: "running" | "completed" | "failed";
  input_summary: string;
  output_summary: string;
  started_at: string;
  finished_at?: string;
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
      steps: s.steps.map((st) => (st.step_id === step_id ? { ...st, ...update } : st)),
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

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  add: (n) =>
    set((s) => ({
      notifications: [n, ...s.notifications].slice(0, 100),
      unreadCount: s.unreadCount + 1,
    })),
  markRead: (id) =>
    set((s) => ({
      notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
      unreadCount: Math.max(0, s.unreadCount - 1),
    })),
  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
}));
```

---

## 8. Framer Motion Configuration

### 8.1 File: `frontend/src/lib/motion.ts`

```tsx
import type { Variants, Transition } from "framer-motion";

// Shared transition presets matching design tokens
export const transitions = {
  micro: { duration: 0.15, ease: [0.25, 1, 0.5, 1] } satisfies Transition,
  default: { duration: 0.25, ease: [0.25, 1, 0.5, 1] } satisfies Transition,
  emphasis: { duration: 0.4, ease: [0.25, 1, 0.5, 1] } satisfies Transition,
  spring: { type: "spring", stiffness: 300, damping: 25 } satisfies Transition,
};

// Reusable animation variants
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.default },
};

export const slideUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: transitions.default },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: transitions.default },
};

export const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

// Property mask blur-to-clear animation
export const redactedReveal: Variants = {
  masked: { filter: "blur(8px)", opacity: 0.6 },
  revealed: { filter: "blur(0px)", opacity: 1, transition: transitions.emphasis },
};
```

---

## 9. Route Structure

```
frontend/src/app/
├── layout.tsx                      # Root layout (fonts, providers)
├── page.tsx                        # Redirect -> /auth/login or /dashboard
├── (public)/                       # No auth required
│   ├── layout.tsx                  # Minimal layout, no sidebar
│   ├── page.tsx                    # Citizen Portal (hero search)
│   └── track/[case_id]/page.tsx   # Case tracking timeline
├── (internal)/                     # Auth required, full AppShell
│   ├── layout.tsx                  # AppShell wrapper
│   ├── intake/page.tsx            # Intake UI
│   ├── trace/[case_id]/page.tsx   # Agent Trace Viewer
│   ├── compliance/[case_id]/page.tsx  # Compliance Workspace
│   ├── inbox/page.tsx             # Department Inbox (Kanban)
│   ├── documents/[id]/page.tsx    # Document Viewer
│   ├── dashboard/page.tsx         # Leadership Dashboard
│   └── security/page.tsx          # Security Console
└── auth/
    └── login/page.tsx             # Login page (mock for dev)
```

### 9.1 Internal Layout: `frontend/src/app/(internal)/layout.tsx`

```tsx
import { AppShell } from "@/components/layout/app-shell";

export default function InternalLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
```

### 9.2 Mock Login Page: `frontend/src/app/auth/login/page.tsx`

```tsx
"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";

const DEMO_USERS = [
  { username: "anh_minh",  label: "Anh Minh (Citizen)",         role: "citizen" },
  { username: "chi_lan",   label: "Chi Lan (Staff Intake)",     role: "staff_intake" },
  { username: "anh_tuan",  label: "Anh Tuan (Staff Processor)", role: "staff_processor" },
  { username: "chi_huong", label: "Chi Huong (Leader)",         role: "leader" },
  { username: "anh_dung",  label: "Anh Dung (Legal)",           role: "legal" },
  { username: "anh_quoc",  label: "Anh Quoc (Security)",        role: "security" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");

  async function handleLogin(username: string) {
    try {
      await login(username, "demo");
      router.push(params.get("redirect") || "/dashboard");
    } catch {
      setError("Login failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
      <div className="w-full max-w-md space-y-6 rounded-lg bg-[var(--bg-surface)] p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">GovFlow Login</h1>
        <p className="text-sm text-[var(--text-secondary)]">Select a demo user:</p>
        <div className="space-y-2">
          {DEMO_USERS.map((u) => (
            <button
              key={u.username}
              onClick={() => handleLogin(u.username)}
              className="w-full rounded-md border border-[var(--border-subtle)] px-4 py-3 text-left text-sm hover:bg-[var(--bg-surface-raised)] transition-colors"
            >
              {u.label}
            </button>
          ))}
        </div>
        {error && <p className="text-sm text-[var(--accent-error)]">{error}</p>}
      </div>
    </div>
  );
}
```

---

## 10. Verification Checklist

```bash
# 1. Dev server starts
cd /home/logan/GovTrack/frontend
npm run dev
# Expected: Compiles successfully, serves on :3000

# 2. Dark mode active by default
# Open http://localhost:3000 -> body has class "dark"
# Toggle to light: background changes from navy-950 to navy-50

# 3. Fonts loaded
# Inspect body -> font-family includes Inter
# Legal sections use Source Serif 4
# Code blocks use JetBrains Mono

# 4. Sidebar navigation
# Click each nav item -> routes to correct path
# Collapse button -> sidebar shrinks to 64px with icons only

# 5. Command palette
# Press Cmd+K -> dialog opens with search input
# Type "intake" -> filters to Intake nav item

# 6. Mock login
# Navigate to /auth/login
# Click "Anh Minh (Citizen)" -> redirects to /dashboard
# Token stored in localStorage under "govflow-token"

# 7. Classification badges render
# Import <ClassificationBadge level="secret" /> -> orange badge
# <ClassificationBadge level="top-secret" /> -> red badge with pulse

# 8. WebSocket connects (requires backend running)
# Open browser console: "[WS] Connected" logged
# wsManager.subscribe("trace", console.log) -> receives test events

# 9. TypeScript compiles clean
npm run build
# Expected: 0 errors
```

---

## Tong ket (Summary)

| Component              | File / Location                              | Status |
|------------------------|----------------------------------------------|--------|
| Design tokens (OKLCH)  | frontend/src/app/globals.css                 | Ready  |
| Font loading           | frontend/src/app/layout.tsx                  | Ready  |
| shadcn/ui + variants   | frontend/src/components/ui/                  | Ready  |
| Dark/light mode        | frontend/src/components/providers/theme-provider.tsx | Ready |
| App shell layout       | frontend/src/components/layout/app-shell.tsx | Ready  |
| Auth provider + mock   | frontend/src/components/providers/auth-provider.tsx | Ready |
| Route middleware        | frontend/src/middleware.ts                   | Ready  |
| API client + TanStack  | frontend/src/lib/api.ts                      | Ready  |
| WebSocket manager      | frontend/src/lib/ws.ts                       | Ready  |
| Zustand stores         | frontend/src/lib/store.ts                    | Ready  |
| Framer Motion config   | frontend/src/lib/motion.ts                   | Ready  |
| Route structure        | frontend/src/app/(public|internal|auth)/     | Ready  |

Next step: proceed to `17-frontend-screens.md` for implementing all 8 screens.
