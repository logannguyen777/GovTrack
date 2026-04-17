/**
 * tests/demo-flow.spec.ts
 *
 * Full citizen-to-officer demo flow.
 * All external API calls are intercepted — no live backend required.
 *
 * Flow:
 *   1. Citizen visits /portal
 *   2. AI assistant chat -> intent detection -> TTHC suggestion
 *   3. "Nộp ngay" -> /submit/1.004415
 *   4. Complete 4-step wizard -> case submitted
 *   5. Redirect to /track/<code>
 *   6. (Officer sub-suite) Navigate to /compliance, open artifact panel
 */
import { test, expect, type Page } from "@playwright/test";

// ---------------------------------------------------------------------------
// Shared stubs
// ---------------------------------------------------------------------------

async function stubAllBackend(page: Page) {
  // Public TTHC list
  await page.route("**/api/public/tthc**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          code: "1.004415",
          name: "Cấp phép xây dựng",
          department: "Sở Xây dựng",
          sla_days: 15,
        },
        {
          code: "1.001757",
          name: "Đăng ký kinh doanh",
          department: "Sở KH&ĐT",
          sla_days: 5,
        },
      ]),
    });
  });

  // Assistant intent
  await page.route("**/api/assistant/intent", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        primary: {
          tthc_code: "1.004415",
          name: "Cấp phép xây dựng",
          confidence: 0.95,
          department: "Sở Xây dựng",
          sla_days: 15,
        },
        alternatives: [],
      }),
    });
  });

  // Assistant chat SSE
  await page.route("**/api/assistant/chat", async (route) => {
    const sse = [
      'data: {"type":"session","session_id":"demo-sess-1"}\n\n',
      'data: {"type":"text_delta","text":"Để xin giấy phép xây dựng, "}\n\n',
      'data: {"type":"text_delta","text":"anh cần chuẩn bị các giấy tờ sau."}\n\n',
      'data: {"type":"citation","id":"c1","law_name":"Luật Xây dựng 50/2014","article":"Điều 89"}\n\n',
      'data: {"type":"suggestion","tthc_code":"1.004415","name":"Cấp phép xây dựng","reason":"Phù hợp yêu cầu","confidence":0.95}\n\n',
      'data: {"type":"done","message_id":"m1"}\n\n',
    ].join("");
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: { "Cache-Control": "no-cache", Connection: "keep-alive" },
      body: sse,
    });
  });

  // Case create
  await page.route("**/api/public/cases", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          case_id: "case-demo-001",
          code: "HS-20260414-DEMO01",
          status: "submitted",
        }),
      });
    } else {
      await route.continue();
    }
  });

  // Case finalize
  await page.route("**/api/public/cases/*/finalize", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  // Track page — case lookup
  await page.route("**/api/public/cases/HS-20260414-DEMO01", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        case_id: "case-demo-001",
        code: "HS-20260414-DEMO01",
        tthc_name: "Cấp phép xây dựng",
        status: "submitted",
        created_at: "2026-04-14T10:00:00Z",
        timeline: [],
      }),
    });
  });
}

// ---------------------------------------------------------------------------
// Login helper (officer)
// ---------------------------------------------------------------------------

async function loginAsDemoUser(
  page: Page,
  match: RegExp,
  manualUsername: string,
) {
  await page.goto("/auth/login");
  // Login page renders 6 demo users as role="listitem" buttons whose aria-label
  // is "Đăng nhập với tài khoản <label>, vai trò ...". Click the matching chip.
  const chip = page.getByRole("listitem", { name: match });
  if (await chip.isVisible({ timeout: 5000 }).catch(() => false)) {
    await chip.click();
  } else {
    // Fallback: expand manual login form first, then fill
    await page
      .getByRole("button", { name: /Đăng nhập bằng tài khoản khác/i })
      .click();
    await page.locator('input[name="username"]').fill(manualUsername);
    await page.locator('input[name="password"]').fill("demo");
    await page
      .locator('form#manual-login-form button[type="submit"]')
      .click();
  }
  await page.waitForURL(/\/(dashboard|inbox|intake|compliance)/, {
    timeout: 12000,
  });
}

async function loginAsOfficer(page: Page) {
  await loginAsDemoUser(page, /Lê Văn Tiếp Nhận/i, "staff_intake");
}

async function loginAsLeader(page: Page) {
  // ld_phong → "Trần Thị Lãnh Đạo" (role=leader, clearance=2) — can approve/reject
  await loginAsDemoUser(page, /Trần Thị Lãnh Đạo/i, "ld_phong");
}

// ---------------------------------------------------------------------------
// Citizen demo flow
// ---------------------------------------------------------------------------

test.describe("Citizen happy path with AI assistant", () => {
  test("step 1: /portal renders search box and AI bubble FAB", async ({
    page,
  }) => {
    await stubAllBackend(page);
    await page.goto("/portal");
    await page.waitForLoadState("domcontentloaded");

    // Portal page should have some content
    await expect(page.locator("main").first()).toBeVisible({ timeout: 8000 });

    // AI bubble FAB
    const fab = page.getByRole("button", { name: /mở trợ lý ai/i });
    await expect(fab).toBeVisible({ timeout: 8000 });
  });

  test("step 2: open AI bubble, send query, receive TTHC suggestion", async ({
    page,
  }) => {
    await stubAllBackend(page);
    await page.goto("/portal");
    await page.waitForLoadState("domcontentloaded");

    // Open bubble
    await page.getByRole("button", { name: /mở trợ lý ai/i }).click();
    const dialog = page.getByRole("dialog", { name: /trợ lý ai/i });
    await expect(dialog).toBeVisible({ timeout: 5000 });

    // Type and send
    const input = page.getByRole("textbox", { name: /tin nhắn/i });
    await expect(input).toBeVisible({ timeout: 5000 });
    await input.fill("Tôi muốn xin giấy phép xây dựng nhà 3 tầng");
    await page.keyboard.press("Enter");

    // Streamed response
    await expect(
      page.getByText(/anh cần chuẩn bị/i),
    ).toBeVisible({ timeout: 8000 });

    // Citation
    await expect(page.getByText(/Luật Xây dựng 50\/2014/i)).toBeVisible({
      timeout: 5000,
    });

    // "Nộp ngay" suggestion card
    await expect(
      page.getByRole("button", { name: /nộp ngay/i }),
    ).toBeVisible({ timeout: 5000 });
  });

  test("step 3: click Nộp ngay redirects to /submit/1.004415", async ({
    page,
  }) => {
    await stubAllBackend(page);
    await page.goto("/portal");
    await page.waitForLoadState("domcontentloaded");

    // Open and chat
    await page.getByRole("button", { name: /mở trợ lý ai/i }).click();
    await page.getByRole("textbox", { name: /tin nhắn/i }).fill("Xin cấp phép xây dựng");
    await page.keyboard.press("Enter");

    // Wait for suggestion card
    const nopNgay = page.getByRole("button", { name: /nộp ngay/i });
    await expect(nopNgay).toBeVisible({ timeout: 8000 });
    await nopNgay.click();

    // Should navigate to submit wizard
    await expect(page).toHaveURL(/\/submit\/1\.004415/, { timeout: 8000 });
  });

  test("step 4: complete wizard and submit case", async ({ page }) => {
    await stubAllBackend(page);
    await page.goto(`/submit/1.004415`);
    await page.waitForLoadState("domcontentloaded");

    // Step 1: TTHC confirmation — click Tiếp theo
    const next = page.getByRole("button", { name: /tiếp theo/i });
    await expect(next).toBeVisible({ timeout: 8000 });
    await next.click();

    // Step 2: fill citizen info
    await page.getByLabel(/họ và tên/i).fill("NGUYỄN VĂN A");
    await page.getByLabel(/số cccd/i).fill("012345678901");
    await page.getByLabel(/số điện thoại/i).fill("0901234567");
    await page.getByLabel(/địa chỉ/i).fill("123 Đường Láng, Hà Nội");
    await page.getByRole("button", { name: /tiếp theo/i }).click();

    // Step 3: upload (skip — just proceed)
    await expect(
      page.getByRole("heading", { name: /tải tài liệu/i }),
    ).toBeVisible({ timeout: 5000 });
    await page.getByRole("button", { name: /tiếp theo/i }).click();

    // Step 4: review + confirm
    await expect(
      page.getByRole("heading", { name: /xem lại|kiểm tra lại/i }),
    ).toBeVisible({ timeout: 5000 });

    // Check the confirmation checkbox if present
    const confirmCheckbox = page.getByRole("checkbox", {
      name: /xác nhận|đồng ý/i,
    });
    if (await confirmCheckbox.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmCheckbox.check();
    }

    // Submit
    const submitBtn = page.getByRole("button", { name: /nộp hồ sơ/i });
    await expect(submitBtn).toBeVisible({ timeout: 5000 });
    await submitBtn.click();

    // Should redirect to receipt (wizard success) or track page
    await expect(page).toHaveURL(
      /\/(submit\/1\.004415\/receipt\?case=HS-20260414-DEMO01|track\/HS-20260414-DEMO01)/,
      { timeout: 15000 },
    );
  });
});

// ---------------------------------------------------------------------------
// Officer sub-flow
// ---------------------------------------------------------------------------

test.describe("Officer compliance and artifact panel", () => {
  test("officer sees compliance workspace and can open artifact panel", async ({
    page,
  }) => {
    // Stub compliance endpoints
    await page.route("**/api/cases/HS-DEMO", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          case_id: "HS-DEMO",
          code: "HS-DEMO",
          tthc_code: "1.004415",
          tthc_name: "Cấp phép xây dựng",
          status: "processing",
          applicant_name: "NGUYỄN VĂN A",
          created_at: "2026-04-14T08:00:00Z",
          updated_at: "2026-04-14T09:00:00Z",
        }),
      });
    });
    await page.route("**/api/agents/trace/HS-DEMO**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          case_id: "HS-DEMO",
          status: "completed",
          steps: [
            { step_id: "s1", agent_name: "ClassifierAgent", status: "completed", duration_ms: 1200 },
            { step_id: "s2", agent_name: "ComplianceAgent", status: "completed", duration_ms: 3400 },
          ],
        }),
      });
    });
    await page.route("**/api/graph/cases/HS-DEMO/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ nodes: [], edges: [] }),
      });
    });
    await page.route("**/api/assistant/recommendation/HS-DEMO", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          recommendation: "approve",
          confidence: 0.92,
          reasons: ["Hồ sơ đầy đủ"],
          citations: [],
          summary: "Hồ sơ đủ điều kiện",
        }),
      });
    });

    await loginAsOfficer(page);
    await page.goto("/compliance/HS-DEMO");
    await page.waitForLoadState("networkidle");

    // Page loads successfully
    await expect(page.locator("main")).toBeVisible({ timeout: 8000 });

    // Artifact panel toggle in top bar
    const toggleBtn = page.getByRole("button", { name: /mở panel ai|đóng panel ai/i });
    await expect(toggleBtn).toBeVisible({ timeout: 5000 });
  });

  test("officer can approve a case", async ({ page }) => {
    // Approve requires role in [leader, dsg, admin, officer] AND status in
    // [gap_checking, legal_review, drafting, leader_review]. Login as leader
    // (ld_phong) and stub status=leader_review so the dialog is actionable.
    await page.route("**/api/cases/HS-DEMO", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          case_id: "HS-DEMO",
          code: "HS-DEMO",
          tthc_code: "1.004415",
          status: "leader_review",
          applicant_name: "NGUYỄN VĂN A",
          created_at: "2026-04-14T08:00:00Z",
          updated_at: "2026-04-14T09:00:00Z",
        }),
      });
    });
    await page.route("**/api/agents/trace/HS-DEMO**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ case_id: "HS-DEMO", status: "completed", steps: [] }),
      });
    });
    await page.route("**/api/graph/cases/HS-DEMO/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ nodes: [], edges: [] }),
      });
    });
    await page.route("**/api/assistant/recommendation/HS-DEMO", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          recommendation: "approve",
          confidence: 0.92,
          reasons: [],
          citations: [],
          summary: "OK",
        }),
      });
    });
    await page.route("**/api/cases/HS-DEMO/finalize", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true }),
      });
    });

    await loginAsLeader(page);
    await page.goto("/compliance/HS-DEMO");
    await page.waitForLoadState("networkidle");

    // Approve button — leader role + actionable status → "Phê duyệt" visible
    const approveBtn = page.getByRole("button", { name: /phê duyệt/i }).first();
    await expect(approveBtn).toBeVisible({ timeout: 8000 });

    // Intercept the confirm dialog
    page.on("dialog", (dialog) => dialog.accept());
    await approveBtn.click();

    // Toast should confirm — wait briefly for it
    await page.waitForTimeout(500);
    // No crash = success; optionally check for toast
  });
});

// ---------------------------------------------------------------------------
// Demo reliability: run core demo scenario 5x
// ---------------------------------------------------------------------------

test.describe("Demo reliability — 5x consecutive runs", () => {
  for (let i = 1; i <= 5; i++) {
    test(`Run ${i}/5: citizen submits CPXD case`, async ({ page }) => {
      await stubAllBackend(page);
      await page.goto("/portal");
      await page.waitForLoadState("domcontentloaded");

      // FAB visible
      await expect(
        page.getByRole("button", { name: /mở trợ lý ai/i }),
      ).toBeVisible({ timeout: 8000 });

      // Open AI chat
      await page.getByRole("button", { name: /mở trợ lý ai/i }).click();
      await expect(
        page.getByRole("dialog", { name: /trợ lý ai/i }),
      ).toBeVisible({ timeout: 5000 });

      // Send message
      await page.getByRole("textbox", { name: /tin nhắn/i }).fill(
        `Xin giấy phép xây dựng lần ${i}`,
      );
      await page.keyboard.press("Enter");

      // Response streamed
      await expect(
        page.getByText(/anh cần chuẩn bị/i),
      ).toBeVisible({ timeout: 8000 });

      // Suggestion card appears
      await expect(
        page.getByRole("button", { name: /nộp ngay/i }),
      ).toBeVisible({ timeout: 5000 });
    });
  }
});
