/**
 * XSS Sanitizer — Unit-level verification for DraftPreview's DOMPurify usage.
 *
 * These tests do NOT require a running server — they use Playwright's evaluate()
 * to run the sanitizer logic in a real browser context (Chromium) which is the
 * most accurate possible test environment for DOM-based XSS.
 *
 * Run with: npx playwright test tests/xss-sanitizer.spec.ts --project=chromium
 */

import { test, expect } from "@playwright/test";

/**
 * Mirror of the DOMPURIFY_CONFIG used in draft-preview.tsx.
 * Kept in sync manually — if you update the allowed-list there,
 * update the string passed to sanitize() in the evaluate() calls below.
 */
const ALLOWED_TAGS = [
  "p", "b", "i", "u",
  "h1", "h2", "h3", "h4",
  "ol", "ul", "li",
  "br", "strong", "em",
  "span", "div",
  "table", "tr", "td", "th", "thead", "tbody",
];
const ALLOWED_ATTR = ["class", "style"];

test.describe("DOMPurify sanitizer — DraftPreview XSS hardening", () => {
  /**
   * Load a minimal HTML page that has isomorphic-dompurify available via CDN
   * so we can evaluate sanitize() calls in a real Chromium DOM.
   */
  test.beforeEach(async ({ page }) => {
    await page.setContent(`
      <!doctype html>
      <html>
        <head>
          <script src="https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js"></script>
        </head>
        <body></body>
      </html>
    `);
    // Wait until DOMPurify is available on the window object.
    await page.waitForFunction(() => typeof (window as unknown as { DOMPurify: unknown }).DOMPurify !== "undefined");
  });

  /** Helper that runs DOMPurify.sanitize() in the browser with the govflow config. */
  async function sanitize(page: import("@playwright/test").Page, input: string): Promise<string> {
    return page.evaluate(
      ({ html, tags, attrs }) => {
        const purify = (window as unknown as { DOMPurify: { sanitize: (h: string, c: object) => string } }).DOMPurify;
        return purify.sanitize(html, {
          ALLOWED_TAGS: tags,
          ALLOWED_ATTR: attrs,
          RETURN_DOM: false,
          RETURN_DOM_FRAGMENT: false,
        });
      },
      { html: input, tags: ALLOWED_TAGS, attrs: ALLOWED_ATTR },
    );
  }

  // -------------------------------------------------------------------------
  // Script injection
  // -------------------------------------------------------------------------

  test("strips <script> tags entirely", async ({ page }) => {
    const result = await sanitize(page, '<script>alert("xss")</script><p>safe</p>');
    expect(result).not.toContain("<script");
    expect(result).not.toContain("alert");
    expect(result).toContain("<p>safe</p>");
  });

  test("strips <img onerror> event handler attack", async ({ page }) => {
    const result = await sanitize(page, '<img src=x onerror=alert(1)><p>content</p>');
    expect(result).not.toContain("<img");
    expect(result).not.toContain("onerror");
    expect(result).not.toContain("alert");
    expect(result).toContain("<p>content</p>");
  });

  test("strips inline event handlers on allowed tags", async ({ page }) => {
    const result = await sanitize(page, '<p onclick="evil()">text</p>');
    expect(result).not.toContain("onclick");
    expect(result).toContain("<p>text</p>");
  });

  test("strips javascript: href on <a> (not in allowed tags)", async ({ page }) => {
    const result = await sanitize(page, '<a href="javascript:alert(1)">click</a>');
    expect(result).not.toContain("javascript:");
    // <a> is not in allowed tags so the whole element should be stripped or
    // reduced to text content.
    expect(result).not.toMatch(/<a\b/i);
  });

  // -------------------------------------------------------------------------
  // Attribute injection
  // -------------------------------------------------------------------------

  test("strips data: URI on src attribute", async ({ page }) => {
    const result = await sanitize(page, '<img src="data:text/html,<script>alert(1)</script>">');
    expect(result).not.toContain("data:");
    expect(result).not.toContain("<script");
  });

  test("strips SVG-based XSS", async ({ page }) => {
    const result = await sanitize(
      page,
      '<svg onload=alert(1)><use href="#x"/></svg>',
    );
    expect(result).not.toContain("onload");
    expect(result).not.toContain("alert");
  });

  test("strips template injection attempt", async ({ page }) => {
    const result = await sanitize(page, "<template><script>alert(1)</script></template>");
    expect(result).not.toContain("<script");
    expect(result).not.toContain("alert");
  });

  // -------------------------------------------------------------------------
  // Allowed content should pass through unchanged
  // -------------------------------------------------------------------------

  test("preserves allowed structure: headings, lists, table", async ({ page }) => {
    const safe = `
      <h2>Tiêu đề</h2>
      <ul><li>Mục 1</li><li>Mục 2</li></ul>
      <table><thead><tr><th>Cột A</th></tr></thead><tbody><tr><td>Giá trị</td></tr></tbody></table>
    `;
    const result = await sanitize(page, safe);
    expect(result).toContain("<h2>");
    expect(result).toContain("<ul>");
    expect(result).toContain("<li>");
    expect(result).toContain("<table>");
    expect(result).toContain("<thead>");
    expect(result).toContain("<th>");
  });

  test("preserves class and style attributes", async ({ page }) => {
    const result = await sanitize(page, '<p class="text-red-500" style="font-weight:bold">OK</p>');
    expect(result).toContain('class="text-red-500"');
    expect(result).toContain('style="font-weight:bold"');
  });

  test("preserves Vietnamese diacritics (UTF-8 round-trip)", async ({ page }) => {
    const vietnamese = "<p>Ủy ban nhân dân tỉnh Bình Dương kính gửi...</p>";
    const result = await sanitize(page, vietnamese);
    expect(result).toContain("Ủy ban nhân dân");
    expect(result).toContain("tỉnh Bình Dương");
  });
});
