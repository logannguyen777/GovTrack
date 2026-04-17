import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  // Tests share persisted zustand stores (artifact-panel, theme) and real
  // backend state. fullyParallel causes cross-test bleed (localStorage race,
  // compliance-page setCase effect interleaving). Keep serial-within-spec
  // and default workers=1 locally (override with --workers flag if needed)
  // — parallel chromium instances can exhaust RAM on dev machines.
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1,
  reporter: "html",
  timeout: 60_000,
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3100",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
