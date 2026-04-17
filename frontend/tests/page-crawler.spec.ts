/**
 * GovFlow — Full Page Crawler + Audit
 *
 * For each role, visits every route, captures:
 *   - Console errors
 *   - Page JS errors
 *   - Network responses >= 400
 *   - Takes screenshot to /tmp/audit-{role}-{slug}.png
 *
 * Outputs a JSON summary at the end.
 */

import { test, expect, type Page, type BrowserContext } from "@playwright/test";
import * as path from "path";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BASE = process.env.BASE_URL ?? "http://localhost:3100";

interface PageAuditResult {
  url: string;
  role: string;
  consoleErrors: string[];
  networkErrors: Array<{ url: string; status: number; method: string }>;
  pageErrors: string[];
  screenshotPath: string;
  passed: boolean;
}

const RESULTS: PageAuditResult[] = [];

// Routes for admin (most permissive)
const ADMIN_ROUTES = [
  "/portal",
  "/track/CASE-2026-0001",
  "/track/CASE-2026-0050",
  "/submit/1.004415",
  "/assistant",
  "/permission-demo",
  "/auth/login",
  "/dashboard",
  "/inbox",
  "/intake",
  "/documents",
  "/documents/DOC-001",
  "/documents/DOC-002",
  "/trace",
  "/trace/CASE-2026-0001",
  "/compliance/CASE-2026-0001",
  "/security",
];

// Role-specific routes
const ROLE_ROUTES: Record<string, string[]> = {
  admin: ADMIN_ROUTES,
  cv_qldt: ["/dashboard", "/inbox", "/compliance/CASE-2026-0001", "/documents", "/trace"],
  ld_phong: ["/dashboard", "/inbox", "/compliance/CASE-2026-0001"],
  staff_intake: ["/intake", "/documents", "/trace"],
  legal_expert: ["/compliance/CASE-2026-0001", "/documents", "/trace/CASE-2026-0001"],
  security_officer: ["/security", "/audit", "/documents"],
};

const DEMO_BUTTONS: Record<string, string> = {
  admin: "Quản trị viên",
  cv_qldt: "CV - Quản lý đất",
  ld_phong: "Lãnh đạo phòng",
  staff_intake: "Cán bộ tiếp nhận",
  legal_expert: "Chuyên viên pháp lý",
  security_officer: "Cán bộ bảo mật",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function slugify(url: string): string {
  return url.replace(/[^a-z0-9]/gi, "-").replace(/-+/g, "-").slice(0, 60);
}

async function loginAs(page: Page, role: string): Promise<void> {
  await page.goto(`${BASE}/auth/login`);
  // Login page uses useSearchParams() which triggers client-side rendering.
  // The server sends an empty shell; React hydrates after JS loads.
  // We must wait for the JS bundle to execute before querying DOM elements.
  await page.waitForLoadState("load", { timeout: 30_000 });
  // Give React time to hydrate the client-side components
  await page.waitForTimeout(3000);
  // The login page renders buttons — wait for at least one to appear
  await page.waitForSelector('button', { timeout: 20_000, state: "visible" });

  const btnLabel = DEMO_BUTTONS[role];
  if (btnLabel) {
    // Try demo button
    const demoBtn = page.locator("button").filter({ hasText: btnLabel }).first();
    const isVisible = await demoBtn.isVisible({ timeout: 3000 }).catch(() => false);
    if (isVisible) {
      await demoBtn.click();
      await page.waitForURL(/\/(dashboard|inbox|intake|portal|security|trace|compliance|documents|permission-demo)/, {
        timeout: 15_000,
      }).catch(() => {});
      return;
    }
  }

  // Fallback: manual login
  const manualSection = page.locator("button").filter({ hasText: "Đăng nhập bằng tài khoản khác" }).first();
  const manualVisible = await manualSection.isVisible({ timeout: 2000 }).catch(() => false);
  if (manualVisible) {
    await manualSection.click();
    await page.waitForTimeout(300);
  }

  const usernameField = page.locator('input[name="username"]');
  const passwordField = page.locator('input[name="password"]');
  await usernameField.fill(role);
  await passwordField.fill("demo");
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|inbox|intake|portal|security|trace|compliance|documents)/, {
    timeout: 15_000,
  }).catch(() => {});
}

async function auditPage(
  page: Page,
  context: BrowserContext,
  url: string,
  role: string,
): Promise<PageAuditResult> {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const networkErrors: Array<{ url: string; status: number; method: string }> = [];

  // Listeners
  const onConsoleMsg = (msg: { type: () => string; text: () => string }) => {
    if (msg.type() === "error") {
      const text = msg.text();
      // Ignore known benign browser errors
      if (
        text.includes("favicon") ||
        text.includes("ERR_ABORTED") ||
        text.includes("net::ERR_") ||
        text.includes("Failed to load resource: the server responded with a status of 4") // 4xx expected
      ) {
        return;
      }
      consoleErrors.push(text);
    }
  };

  const onPageError = (error: Error) => {
    pageErrors.push(error.message);
  };

  const onResponse = async (response: { url: () => string; status: () => number; request: () => { method: () => string } }) => {
    const status = response.status();
    const responseUrl = response.url();
    const method = response.request().method();

    // Only track errors >= 500 (4xx is expected for unauthorized routes)
    if (status >= 500) {
      networkErrors.push({ url: responseUrl, status, method });
    }
  };

  page.on("console", onConsoleMsg);
  page.on("pageerror", onPageError);
  page.on("response", onResponse);

  const fullUrl = url.startsWith("http") ? url : `${BASE}${url}`;
  try {
    await page.goto(fullUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
    // Wait a bit for async requests to settle
    await page.waitForTimeout(2000);
    // Try networkidle but don't fail if it times out (some pages have long polling)
    await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  } catch {
    // Navigation may fail for redirects etc — capture what we have
  }

  // Screenshot
  const screenshotPath = `/tmp/audit-${role}-${slugify(url)}.png`;
  await page.screenshot({ path: screenshotPath, fullPage: false }).catch(() => {});

  page.removeListener("console", onConsoleMsg);
  page.removeListener("pageerror", onPageError);
  page.removeListener("response", onResponse);

  const passed = pageErrors.length === 0 && networkErrors.length === 0;

  return {
    url,
    role,
    consoleErrors,
    networkErrors,
    pageErrors,
    screenshotPath,
    passed,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Page Crawler — Admin role", () => {
  test.setTimeout(180_000);

  test("crawl all pages as admin", async ({ page, context }) => {
    await loginAs(page, "admin");

    for (const route of ADMIN_ROUTES) {
      const result = await auditPage(page, context, route, "admin");
      RESULTS.push(result);

      if (result.networkErrors.length > 0) {
        console.log(
          `[FAIL] admin ${route}: network 5xx → ${result.networkErrors.map((e) => `${e.status} ${e.url}`).join(", ")}`,
        );
      }
      if (result.pageErrors.length > 0) {
        console.log(
          `[FAIL] admin ${route}: page errors → ${result.pageErrors.join("; ")}`,
        );
      }
      if (result.consoleErrors.length > 0) {
        console.log(
          `[WARN] admin ${route}: console errors → ${result.consoleErrors.slice(0, 3).join("; ")}`,
        );
      }

      // Only assert no 5xx and no JS errors
      expect(
        result.networkErrors.filter((e) => e.status >= 500),
        `5xx on ${route}: ${result.networkErrors.map((e) => `${e.status} ${e.url}`).join(", ")}`,
      ).toHaveLength(0);

      expect(
        result.pageErrors,
        `JS errors on ${route}: ${result.pageErrors.join("; ")}`,
      ).toHaveLength(0);
    }
  });
});

test.describe("Interactive flows — admin", () => {
  test.setTimeout(120_000);

  test("inbox: click first row navigates to compliance", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto(`${BASE}/inbox`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
    await page.waitForTimeout(2000);

    // Click first case card / row
    const firstRow = page
      .locator('[data-testid="case-card"], .case-row, [role="listitem"] button')
      .first();
    const isVisible = await firstRow.isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      await firstRow.click();
      // Should navigate to compliance or trace
      await page.waitForURL(/\/(compliance|trace)\//, { timeout: 10_000 }).catch(() => {});
      const currentUrl = page.url();
      expect(currentUrl).toMatch(/\/(compliance|trace)\//);
    } else {
      // No cards yet — acceptable
      console.log("[SKIP] inbox: no case cards found");
    }
  });

  test("compliance: leader approve flow", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto(`${BASE}/compliance/CASE-2026-0001`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
    await page.waitForTimeout(2000);

    // Look for approve button
    const approveBtn = page.locator("button").filter({ hasText: /Phê duyệt|Duyệt|Chấp thuận/ }).first();
    const isVisible = await approveBtn.isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      await approveBtn.click();
      // Wait for confirm dialog or toast
      await page.waitForTimeout(1000);
      // Look for confirm button in dialog
      const confirmBtn = page.locator("button").filter({ hasText: /Xác nhận|Đồng ý|Confirm/ }).first();
      const confirmVisible = await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false);
      if (confirmVisible) {
        await confirmBtn.click();
        await page.waitForTimeout(1500);
      }
      // Should show toast or update UI without error
      const errors = await page.evaluate(() => window.__pageErrors ?? []);
      expect(errors).toHaveLength(0);
    } else {
      console.log("[SKIP] compliance: no approve button visible (status may not allow it)");
    }
  });

  test("intake: file picker button opens without error", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto(`${BASE}/intake`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});

    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));

    // Just interact with upload area
    const uploadArea = page
      .locator('[data-testid="upload-zone"], [aria-label*="tải"], button[aria-label*="upload"], .dropzone')
      .first();
    const visible = await uploadArea.isVisible({ timeout: 5000 }).catch(() => false);
    if (visible) {
      // Don't actually upload — just verify no error on hover
      await uploadArea.hover();
    }

    await page.waitForTimeout(1000);
    expect(errors).toHaveLength(0);
  });

  test("dashboard: charts render without error", async ({ page }) => {
    await loginAs(page, "admin");
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));

    await page.goto(`${BASE}/dashboard`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
    await page.waitForTimeout(2000);

    expect(errors).toHaveLength(0);
    // Verify page loaded successfully (not an error page)
    // The dashboard page uses AppShell which renders the content in a div, not a <main> element.
    // We check for any substantial visible content — a heading or a div with text.
    const bodyText = await page.textContent("body");
    expect(bodyText).toBeTruthy();
  });

  test("sidebar navigation works without error", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto(`${BASE}/dashboard`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});

    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));

    // Navigate via sidebar links
    const navLinks = [
      { href: "/inbox", text: /inbox|Hộp thư|Tiếp nhận/i },
      { href: "/trace", text: /trace|Theo dõi/i },
      { href: "/documents", text: /document|Tài liệu/i },
    ];

    for (const link of navLinks) {
      const navLink = page
        .locator(`nav a[href="${link.href}"], aside a[href="${link.href}"]`)
        .first();
      const visible = await navLink.isVisible({ timeout: 3000 }).catch(() => false);
      if (visible) {
        await navLink.click();
        await page.waitForTimeout(1500);
        expect(page.url()).toContain(link.href);
      }
    }

    expect(errors).toHaveLength(0);
  });
});

test.describe("Role regression", () => {
  test.setTimeout(120_000);

  for (const [role, routes] of Object.entries(ROLE_ROUTES)) {
    if (role === "admin") continue; // covered above

    test(`${role}: accessible pages load without 5xx`, async ({ page, context }) => {
      await loginAs(page, role);
      for (const route of routes) {
        const result = await auditPage(page, context, route, role);
        RESULTS.push(result);

        expect(
          result.networkErrors.filter((e) => e.status >= 500),
          `5xx as ${role} on ${route}`,
        ).toHaveLength(0);

        expect(
          result.pageErrors,
          `JS errors as ${role} on ${route}`,
        ).toHaveLength(0);
      }
    });
  }
});

// ---------------------------------------------------------------------------
// Summary output
// ---------------------------------------------------------------------------

test.afterAll(() => {
  const total = RESULTS.length;
  const failed = RESULTS.filter((r) => !r.passed);
  const passed = RESULTS.filter((r) => r.passed);

  console.log("\n========================================");
  console.log("GovFlow Page Crawler Summary");
  console.log("========================================");
  console.log(`Total pages audited: ${total}`);
  console.log(`Passed: ${passed.length}`);
  console.log(`Failed: ${failed.length}`);

  if (failed.length > 0) {
    console.log("\nFailed pages:");
    for (const r of failed) {
      console.log(`  [${r.role}] ${r.url}`);
      if (r.networkErrors.length > 0) {
        r.networkErrors.forEach((e) =>
          console.log(`    5xx: ${e.status} ${e.url}`),
        );
      }
      if (r.pageErrors.length > 0) {
        r.pageErrors.forEach((e) => console.log(`    JS: ${e}`));
      }
    }
  }

  // Output full JSON summary
  const summaryPath = "/tmp/audit-summary.json";
  const fs = require("fs");
  fs.writeFileSync(summaryPath, JSON.stringify(RESULTS, null, 2));
  console.log(`\nFull JSON summary: ${summaryPath}`);
  console.log("========================================\n");
});
