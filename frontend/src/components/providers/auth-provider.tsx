"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import type { User, LoginResponse } from "@/lib/types";

interface AuthCtx {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  login: async () => {},
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

  useEffect(() => {
    const storedToken = localStorage.getItem("govflow-token");
    const storedUser = localStorage.getItem("govflow-user");
    if (storedToken) {
      setToken(storedToken);
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
    setToken(data.access_token);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("govflow-token");
    localStorage.removeItem("govflow-user");
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
