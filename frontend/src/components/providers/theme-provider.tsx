"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light" | "system";

interface ThemeCtx {
  theme: Theme;
  setTheme: (t: Theme) => void;
  resolved: "dark" | "light";
}

const ThemeContext = createContext<ThemeCtx>({
  theme: "light",
  setTheme: () => {},
  resolved: "light",
});

export function ThemeProvider({
  children,
  defaultTheme: _defaultTheme = "light",
  storageKey: _storageKey = "govflow-theme",
}: {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}) {
  const [theme, setThemeState] = useState<Theme>("light");
  const resolved: "light" = "light";

  useEffect(() => {
    document.documentElement.classList.remove("dark");
    try {
      localStorage.setItem(_storageKey, "light");
    } catch {}
  }, [_storageKey]);

  const setTheme = (_t: Theme) => {
    setThemeState("light");
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolved }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
