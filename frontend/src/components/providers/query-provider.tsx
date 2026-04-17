"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

// ---------------------------------------------------------------------------
// Singleton QueryClient — exported so non-React code (api.ts, ws.ts) can
// call queryClient.clear() or invalidateQueries() without hooks.
// ---------------------------------------------------------------------------
let _singletonClient: QueryClient | null = null;

export function getQueryClient(): QueryClient {
  if (!_singletonClient) {
    _singletonClient = createQueryClient();
  }
  return _singletonClient;
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        gcTime: 5 * 60_000,
        retry: 3,
        retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30_000),
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
      },
      mutations: {
        retry: 1,
      },
    },
  });
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => {
    const c = createQueryClient();
    // Keep singleton in sync with the React-tree instance
    _singletonClient = c;
    return c;
  });

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
