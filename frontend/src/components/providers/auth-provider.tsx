"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import type { User, LoginResponse } from "@/lib/types";
import { registerUnauthorizedHandler } from "@/lib/api";

interface AuthCtx {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  login: async () => ({ user_id: "", username: "", role: "", clearance_level: 0, departments: [] }),
  logout: () => {},
  isLoading: true,
});

function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return {};
  }
}

function userFromToken(token: string, loginData?: LoginResponse): User {
  const payload = decodeJwtPayload(token);
  return {
    user_id: (loginData?.user_id ?? payload.sub ?? "") as string,
    username: (payload.username ?? loginData?.user_id ?? "") as string,
    full_name: loginData?.full_name || (payload.full_name as string | undefined),
    role: (loginData?.role ?? payload.role ?? "") as string,
    clearance_level: (loginData?.clearance_level ??
      payload.clearance_level ??
      0) as number,
    departments: (payload.departments ?? []) as string[],
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const queryClient = useQueryClient();

  // Rehydrate from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("govflow-token");
    const storedUser = localStorage.getItem("govflow-user");
    if (storedToken) {
      setToken(storedToken);
      // Re-sync cookie mirror (in case it expired or was cleared by browser).
      document.cookie = `govflow-token=${storedToken}; path=/; SameSite=Lax`;
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          setUser(userFromToken(storedToken));
        }
      } else {
        setUser(userFromToken(storedToken));
      }
    }
    setIsLoading(false);
  }, []);

  // Register the 401 handler so api.ts can redirect without a circular import
  useEffect(() => {
    registerUnauthorizedHandler((currentPath: string) => {
      queryClient.clear();
      setToken(null);
      setUser(null);
      const next = encodeURIComponent(currentPath);
      router.replace(`/auth/login?next=${next}`);
    });
  }, [queryClient, router]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error("Login failed");
    const data: LoginResponse = await res.json();
    const u = userFromToken(data.access_token, data);
    localStorage.setItem("govflow-token", data.access_token);
    localStorage.setItem("govflow-user", JSON.stringify(u));
    // Mirror token to a cookie so middleware can read it (localStorage is
    // client-only; middleware runs on the Edge before JS executes).
    document.cookie = `govflow-token=${data.access_token}; path=/; SameSite=Lax`;
    setToken(data.access_token);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(() => {
    const currentToken = localStorage.getItem("govflow-token");
    // Best-effort server-side token revocation (Wave 0.2).
    // Fire-and-forget — UI proceeds immediately regardless of response.
    if (currentToken) {
      fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` },
      }).catch(() => { /* silenced — revocation is best-effort */ });
    }
    localStorage.removeItem("govflow-token");
    localStorage.removeItem("govflow-user");
    // Clear cookie mirror so middleware redirects correctly on next navigation.
    document.cookie = "govflow-token=; path=/; max-age=0; SameSite=Lax";
    queryClient.clear();
    setToken(null);
    setUser(null);
    router.push("/auth/login");
  }, [queryClient, router]);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
