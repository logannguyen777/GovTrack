/**
 * tests/assistant-bubble.spec.ts
 *
 * Playwright E2E tests for the AIAssistantBubble component.
 * Uses Playwright route interception to mock SSE and document-extract endpoints.
 * No live backend required — all network calls are stubbed.
 */
import { test, expect, type Page } from "@playwright/test";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Open /portal and wait for the page to settle. */
async function gotoPortal(page: Page) {
  await page.goto("/portal");
  await page.waitForLoadState("domcontentloaded");
}

/** Find the AI FAB by aria-label.  The component uses "Mở trợ lý AI" when closed. */
async function openBubble(page: Page) {
  const fab = page.getByRole("button", { name: /mở trợ lý ai/i });
  await expect(fab).toBeVisible({ timeout: 8000 });
  await fab.click();
}

// SSE body for a simple chat response
const MOCK_SSE_CHAT = [
  'data: {"type":"session","session_id":"test-sess-1"}\n\n',
  'data: {"type":"text_delta","text":"Để xin "}\n\n',
  'data: {"type":"text_delta","text":"giấy phép xây dựng, "}\n\n',
  'data: {"type":"text_delta","text":"anh cần các giấy tờ sau: Đơn đề nghị, bản vẽ thiết kế."}\n\n',
  'data: {"type":"citation","id":"cit-1","law_name":"NĐ 53/2017","article":"Điều 12"}\n\n',
  'data: {"type":"suggestion","tthc_code":"1.004415","name":"Cấp phép xây dựng","reason":"Phù hợp với yêu cầu","confidence":0.95}\n\n',
  'data: {"type":"done","message_id":"msg-1"}\n\n',
].join("");

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

test.describe("AIAssistantBubble", () => {
  test("bubble FAB is visible on /portal and opens panel with animation", async ({
    page,
  }) => {
    await gotoPortal(page);

    // FAB should be present before opening
    const fab = page.getByRole("button", { name: /mở trợ lý ai/i });
    await expect(fab).toBeVisible({ timeout: 8000 });

    await fab.click();

    // After click, the dialog (role=dialog aria-label="Trợ lý AI") should appear
    const dialog = page.getByRole("dialog", { name: /trợ lý ai/i });
    await expect(dialog).toBeVisible({ timeout: 5000 });
  });

  test("welcome state renders 4 quick-intent chips for portal context", async ({
    page,
  }) => {
    await gotoPortal(page);
    await openBubble(page);

    // Scope chip queries to the AI assistant dialog — portal itself also has
    // "Cấp phép xây dựng" buttons in TTHC cards and history list.
    const dialog = page.getByRole("dialog", { name: /trợ lý ai/i });
    await expect(
      dialog.getByRole("button", { name: /cấp phép xây dựng/i }),
    ).toBeVisible({ timeout: 5000 });
    await expect(
      dialog.getByRole("button", { name: /tra cứu hồ sơ/i }),
    ).toBeVisible();
    await expect(
      dialog.getByRole("button", { name: /giấy tờ cần/i }),
    ).toBeVisible();
    await expect(
      dialog.getByRole("button", { name: /hướng dẫn bước nộp/i }),
    ).toBeVisible();
  });

  test("send message streams response and shows citation + Nộp ngay button", async ({
    page,
  }) => {
    // Intercept the SSE chat endpoint before page load
    await page.route("**/api/assistant/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: {
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
          "X-Accel-Buffering": "no",
        },
        body: MOCK_SSE_CHAT,
      });
    });

    await gotoPortal(page);
    await openBubble(page);

    // Locate the composer textarea by its aria-label
    const input = page.getByRole("textbox", { name: /tin nhắn/i });
    await expect(input).toBeVisible({ timeout: 5000 });
    await input.fill("Tôi muốn xin cấp phép xây dựng");
    await page.keyboard.press("Enter");

    // Streamed text should appear in the message log
    await expect(
      page.getByText(/anh cần các giấy tờ sau/i),
    ).toBeVisible({ timeout: 8000 });

    // Citation chip rendered inside ChatMessageBubble
    await expect(page.getByText(/NĐ 53\/2017/)).toBeVisible({ timeout: 5000 });

    // Suggestion card "Nộp ngay" button rendered after done event
    await expect(
      page.getByRole("button", { name: /nộp ngay/i }),
    ).toBeVisible({ timeout: 5000 });
  });

  test("clicking a quick-intent chip sends a message automatically", async ({
    page,
  }) => {
    await page.route("**/api/assistant/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          'data: {"type":"session","session_id":"s2"}\n\n',
          'data: {"type":"text_delta","text":"Để xây dựng cần..."}\n\n',
          'data: {"type":"done"}\n\n',
        ].join(""),
      });
    });

    await gotoPortal(page);
    await openBubble(page);

    // Click a quick intent chip — scope to dialog to avoid portal duplicates.
    const dialog = page.getByRole("dialog", { name: /trợ lý ai/i });
    const chip = dialog.getByRole("button", { name: /cấp phép xây dựng/i });
    await expect(chip).toBeVisible({ timeout: 5000 });
    await chip.click();

    // A response should stream back
    await expect(
      page.getByText(/để xây dựng cần/i),
    ).toBeVisible({ timeout: 8000 });
  });

  test("attach document triggers extraction UI with entity card", async ({
    page,
  }) => {
    // Stub the extraction endpoint
    await page.route("**/api/documents/extract", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          extraction_id: "ext-1",
          document_type: "CCCD",
          entities: [
            { key: "full_name", value: "NGUYỄN VĂN A", confidence: 0.96 },
            { key: "cccd", value: "012345678901", confidence: 0.94 },
          ],
          raw_text: "...",
          confidence: 0.95,
        }),
      });
    });

    // Also stub the chat endpoint so the assistant message is sent
    await page.route("**/api/assistant/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          'data: {"type":"session","session_id":"s3"}\n\n',
          'data: {"type":"done"}\n\n',
        ].join(""),
      });
    });

    await gotoPortal(page);
    await openBubble(page);

    // The file input in the Composer is visually hidden (sr-only) but still attached
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached({ timeout: 5000 });

    // Use setInputFiles directly — bypasses the hidden input restriction
    await fileInput.setInputFiles({
      name: "cccd_front.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("fake-image-data"),
    });

    // The DocumentAIExtractor card should appear — scope to dialog + use
    // first() since the extracted value may appear in multiple slots.
    const dialog = page.getByRole("dialog", { name: /trợ lý ai/i });
    await expect(
      dialog.getByText(/CCCD|NGUYỄN VĂN A|012345678901|ext-1/i).first(),
    ).toBeVisible({ timeout: 8000 });
  });

  test("Escape key closes the bubble panel", async ({ page }) => {
    await gotoPortal(page);
    await openBubble(page);

    const dialog = page.getByRole("dialog", { name: /trợ lý ai/i });
    await expect(dialog).toBeVisible({ timeout: 5000 });

    await page.keyboard.press("Escape");

    await expect(dialog).toBeHidden({ timeout: 3000 });
  });

  test("error response shows banner in panel", async ({ page }) => {
    await page.route("**/api/assistant/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: [
          'data: {"type":"session","session_id":"s4"}\n\n',
          'data: {"type":"error","message":"Dịch vụ tạm thời gián đoạn"}\n\n',
        ].join(""),
      });
    });

    await gotoPortal(page);
    await openBubble(page);

    const input = page.getByRole("textbox", { name: /tin nhắn/i });
    await input.fill("test lỗi");
    await page.keyboard.press("Enter");

    // The error banner (role=alert) should appear — next.js also injects
    // __next-route-announcer__ with role=alert, so match by text content.
    await expect(
      page.getByRole("alert").filter({ hasText: /gián đoạn|lỗi|error/i }),
    ).toBeVisible({ timeout: 8000 });
  });
});
