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
      ? typeof window !== "undefined" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
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
