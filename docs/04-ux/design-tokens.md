# Design Tokens — 3-tier token architecture

> Canonical token reference for GovFlow. Consumed by Tailwind CSS v4 `@theme` directives and Framer Motion config. Every color, type, motion, elevation, and spacing value in the UI MUST resolve to a token defined here — no hand-tuned hex, no inline durations.

**Why this doc exists (separate from [design-system.md](./design-system.md)):** design-system.md catalogs *components*; this doc catalogs the *values* those components consume. Frontend team copy-pastes this file into `frontend/styles/tokens.css` on day 1, then never touches primitive values again — they only reference semantic tokens downstream.

**Reading order:** §1 tier architecture → §2 color → §3 typography → §4 motion → §5 elevation → §6 spacing/radius → §7 focus ring → §8 how to use.

---

## 1. Tier architecture

GovFlow uses the industry-standard **3-tier token model** (Material 3, Radix Themes, Figma Tokens Studio):

```
┌─────────────────────────────────────────────────────┐
│  Tier 1: PRIMITIVE tokens (raw values)              │
│  --gov-neutral-1 .. -12, --gov-accent-1 .. -12      │
│  Never referenced directly by components.           │
└─────────────────────────┬───────────────────────────┘
                          │ referenced by
┌─────────────────────────▼───────────────────────────┐
│  Tier 2: SEMANTIC tokens (role-based)               │
│  --color-surface-page, --color-text-primary         │
│  Name describes PURPOSE, never current color.       │
│  Dark/light mode swap happens here.                 │
└─────────────────────────┬───────────────────────────┘
                          │ referenced by
┌─────────────────────────▼───────────────────────────┐
│  Tier 3: COMPONENT tokens (per-component overrides) │
│  --card-bg, --button-primary-hover-bg               │
│  Optional — only when component needs divergence.   │
└─────────────────────────────────────────────────────┘
```

**Rules:**

- **Components consume tier 2 or tier 3, NEVER tier 1.** A button referencing `--gov-accent-9` directly breaks retheming. It must reference `--color-action-solid` which points to `--gov-accent-9`.
- **Semantic tokens are named by ROLE, never by current color.** `--color-action-solid` is right; `--color-blue-primary` is wrong — on the day the brand shifts to a deeper indigo, the second name becomes a lie.
- **Dark mode swap happens ONLY at tier 2.** Primitives stay constant; the `:root` vs `.dark` scope re-maps semantic tokens to different primitive steps. Components don't care which mode is active.
- **Tier 3 is optional.** Only add a component token when the component needs a value divergent from the semantic layer (rare) — e.g. a Card component that uses a subtly lighter bg than general `--color-surface-card`.

**Reference:** [Martin Fowler — Design Token-Based UI Architecture](https://martinfowler.com/articles/design-token-based-ui-architecture.html), [Material 3 design tokens](https://m3.material.io/foundations/design-tokens).

---

## 2. Color — OKLCH primitives + Radix 12-step scale

### Why OKLCH in 2026

- **Perceptually uniform lightness.** `oklch(0.55 0.18 265)` and `oklch(0.55 0.18 25)` look equally dark to the human eye — HSL does not have this property. Classification colors at matched "visual weight" matter for gov tech (unclassified green shouldn't feel lighter than confidential amber when both are step-9).
- **Clean programmatic ramps.** Hold L and C constant, rotate H → get perfectly matched palettes for accent/success/warning/danger.
- **P3 wide gamut** with automatic sRGB fallback. Modern displays get richer colors; old displays degrade gracefully.
- **Production-ready.** All evergreen browsers since early 2025; default color space in Tailwind v4 and shadcn's default template.

Reference: [Evil Martians — OKLCH in Tailwind](https://evilmartians.com/chronicles/better-dynamic-themes-in-tailwind-with-oklch-color-magic).

### Radix 12-step semantic scale

Each palette ships **12 steps** plus 12 alpha variants. Semantic meaning (copy from Radix):

| Step | Use for |
|---|---|
| 1 | App background |
| 2 | Subtle background (cards, sidebars) |
| 3 | UI element background |
| 4 | Hovered UI element background |
| 5 | Active/selected UI element background |
| 6 | Subtle borders, separators |
| 7 | UI element border, focus ring |
| 8 | Hovered UI element border |
| 9 | Solid backgrounds (buttons, badges) |
| 10 | Hovered solid backgrounds |
| 11 | Low-contrast text |
| 12 | High-contrast text |

**You reference `--gov-accent-9` for a primary button, never `#2563EB`.** When brand refreshes, only tier 1 changes — all components retint for free.

Reference: [Radix Themes — Color](https://www.radix-ui.com/themes/docs/theme/color).

### Primitive ramps (tier 1)

All ramps live in `frontend/styles/tokens/color.css`. Dark mode values shown; light mode in §2.4.

```css
:root {
  /* Neutral (court gray — base for surfaces/text) */
  --gov-neutral-1:  oklch(0.14 0.008 265);  /* app bg */
  --gov-neutral-2:  oklch(0.17 0.010 265);  /* subtle bg */
  --gov-neutral-3:  oklch(0.21 0.012 265);
  --gov-neutral-4:  oklch(0.24 0.014 265);
  --gov-neutral-5:  oklch(0.28 0.016 265);
  --gov-neutral-6:  oklch(0.33 0.018 265);  /* subtle border */
  --gov-neutral-7:  oklch(0.40 0.020 265);
  --gov-neutral-8:  oklch(0.50 0.022 265);
  --gov-neutral-9:  oklch(0.62 0.024 265);  /* solid neutral */
  --gov-neutral-10: oklch(0.68 0.022 265);
  --gov-neutral-11: oklch(0.78 0.018 265);  /* low-contrast text */
  --gov-neutral-12: oklch(0.96 0.008 265);  /* high-contrast text */

  /* Accent (court navy — primary action) */
  --gov-accent-1:  oklch(0.15 0.030 255);
  --gov-accent-2:  oklch(0.19 0.050 255);
  --gov-accent-3:  oklch(0.24 0.080 255);
  --gov-accent-4:  oklch(0.28 0.110 255);
  --gov-accent-5:  oklch(0.33 0.140 255);
  --gov-accent-6:  oklch(0.38 0.160 255);
  --gov-accent-7:  oklch(0.44 0.175 255);
  --gov-accent-8:  oklch(0.50 0.185 255);
  --gov-accent-9:  oklch(0.55 0.195 255);  /* primary button */
  --gov-accent-10: oklch(0.60 0.190 255);
  --gov-accent-11: oklch(0.72 0.160 255);
  --gov-accent-12: oklch(0.92 0.060 255);

  /* Success (approve, on-track SLA, valid) */
  --gov-success-1:  oklch(0.16 0.020 155);
  --gov-success-2:  oklch(0.20 0.035 155);
  --gov-success-3:  oklch(0.25 0.060 155);
  --gov-success-4:  oklch(0.30 0.085 155);
  --gov-success-5:  oklch(0.36 0.110 155);
  --gov-success-6:  oklch(0.42 0.130 155);
  --gov-success-7:  oklch(0.48 0.145 155);
  --gov-success-8:  oklch(0.54 0.160 155);
  --gov-success-9:  oklch(0.60 0.170 155);  /* approve button */
  --gov-success-10: oklch(0.65 0.165 155);
  --gov-success-11: oklch(0.75 0.140 155);
  --gov-success-12: oklch(0.93 0.060 155);

  /* Warning (gap, at-risk SLA, amber flag) */
  --gov-warning-1:  oklch(0.18 0.025 75);
  --gov-warning-2:  oklch(0.22 0.045 75);
  --gov-warning-3:  oklch(0.28 0.075 75);
  --gov-warning-4:  oklch(0.34 0.105 75);
  --gov-warning-5:  oklch(0.40 0.130 75);
  --gov-warning-6:  oklch(0.46 0.150 75);
  --gov-warning-7:  oklch(0.52 0.165 75);
  --gov-warning-8:  oklch(0.58 0.175 75);
  --gov-warning-9:  oklch(0.68 0.180 75);  /* amber badge */
  --gov-warning-10: oklch(0.73 0.170 75);
  --gov-warning-11: oklch(0.82 0.140 75);
  --gov-warning-12: oklch(0.95 0.060 75);

  /* Danger (denied, overdue, error) */
  --gov-danger-1:  oklch(0.16 0.025 25);
  --gov-danger-2:  oklch(0.20 0.045 25);
  --gov-danger-3:  oklch(0.25 0.075 25);
  --gov-danger-4:  oklch(0.30 0.105 25);
  --gov-danger-5:  oklch(0.36 0.130 25);
  --gov-danger-6:  oklch(0.42 0.150 25);
  --gov-danger-7:  oklch(0.48 0.170 25);
  --gov-danger-8:  oklch(0.54 0.185 25);
  --gov-danger-9:  oklch(0.58 0.200 25);  /* destructive button */
  --gov-danger-10: oklch(0.63 0.195 25);
  --gov-danger-11: oklch(0.75 0.160 25);
  --gov-danger-12: oklch(0.93 0.060 25);

  /* Classification ramps — 4 full palettes, not single colors.
     Each ramp provides banner bg (9), banner text (12), portion pill bg (4),
     redact bar (neutral-1), subtle tint for card backgrounds (2). */
  --gov-class-unclass-1..12:    /* emerald ramp, H=155 */;
  --gov-class-confid-1..12:     /* blue ramp, H=255 */;
  --gov-class-secret-1..12:     /* orange ramp, H=55 */;
  --gov-class-topsec-1..12:     /* red ramp, H=20 */;
}
```

**Alpha variants** (`-a1..-a12`) for glass/overlay effects are auto-generated by a build step — see [OKLCH in Tailwind article](https://evilmartians.com/chronicles/better-dynamic-themes-in-tailwind-with-oklch-color-magic) for the generator.

### Semantic tokens (tier 2)

Components consume ONLY these names. Dark mode default shown; light mode overrides in §2.4.

```css
:root {
  /* Surfaces — the "layers" of the UI */
  --color-surface-page:       var(--gov-neutral-1);   /* app root bg */
  --color-surface-subtle:     var(--gov-neutral-2);   /* card bg, sidebar */
  --color-surface-card:       var(--gov-neutral-3);   /* raised card */
  --color-surface-elevated:   var(--gov-neutral-4);   /* modal, popover */
  --color-surface-inset:      var(--gov-neutral-2);   /* graph canvas, code block */
  --color-surface-overlay:    color-mix(in oklch, var(--gov-neutral-1) 60%, transparent);

  /* Text */
  --color-text-primary:       var(--gov-neutral-12);
  --color-text-secondary:     var(--gov-neutral-11);
  --color-text-muted:         var(--gov-neutral-10);
  --color-text-disabled:      var(--gov-neutral-8);
  --color-text-on-accent:     var(--gov-neutral-12);  /* text on --color-action-solid */
  --color-text-on-danger:     var(--gov-neutral-12);
  --color-text-link:          var(--gov-accent-11);

  /* Borders */
  --color-border-subtle:      var(--gov-neutral-5);
  --color-border-default:     var(--gov-neutral-6);
  --color-border-strong:      var(--gov-neutral-7);
  --color-border-focus:       var(--gov-accent-8);

  /* Action (primary interactive) */
  --color-action-solid:       var(--gov-accent-9);
  --color-action-hover:       var(--gov-accent-10);
  --color-action-active:      var(--gov-accent-8);
  --color-action-disabled:    var(--gov-accent-5);
  --color-action-fg:          var(--gov-neutral-12);

  /* Status — 4 semantic families × 3 parts each */
  --color-status-success-bg:     var(--gov-success-3);
  --color-status-success-fg:     var(--gov-success-11);
  --color-status-success-border: var(--gov-success-7);
  --color-status-success-solid:  var(--gov-success-9);

  --color-status-warning-bg:     var(--gov-warning-3);
  --color-status-warning-fg:     var(--gov-warning-11);
  --color-status-warning-border: var(--gov-warning-7);
  --color-status-warning-solid:  var(--gov-warning-9);

  --color-status-danger-bg:      var(--gov-danger-3);
  --color-status-danger-fg:      var(--gov-danger-11);
  --color-status-danger-border:  var(--gov-danger-7);
  --color-status-danger-solid:   var(--gov-danger-9);

  --color-status-info-bg:        var(--gov-accent-3);
  --color-status-info-fg:        var(--gov-accent-11);
  --color-status-info-border:    var(--gov-accent-7);
  --color-status-info-solid:     var(--gov-accent-9);

  /* Classification — banner, portion pill, redact bar */
  --color-class-unclass-banner:  var(--gov-class-unclass-9);
  --color-class-unclass-text:    var(--gov-class-unclass-12);
  --color-class-unclass-tint:    var(--gov-class-unclass-2);

  --color-class-confid-banner:   var(--gov-class-confid-9);
  --color-class-confid-text:     var(--gov-class-confid-12);
  --color-class-confid-tint:     var(--gov-class-confid-2);

  --color-class-secret-banner:   var(--gov-class-secret-9);
  --color-class-secret-text:     var(--gov-class-secret-12);
  --color-class-secret-tint:     var(--gov-class-secret-2);

  --color-class-topsec-banner:   var(--gov-class-topsec-9);
  --color-class-topsec-text:     var(--gov-class-topsec-12);
  --color-class-topsec-tint:     var(--gov-class-topsec-2);

  --color-redact-bar:            var(--gov-neutral-1);   /* solid bar, not blur */
}
```

**Rule — every semantic color MUST have a paired `-fg`/`-text` token** (shadcn convention) so AA contrast (≥ 4.5:1 body, ≥ 3:1 large text) is never ambiguous. Build-time lint enforces.

### Light mode overrides

Citizen Portal defaults to light; internal workspace defaults to dark. Light mode scope:

```css
.light {
  --color-surface-page:     var(--gov-neutral-12);  /* inverted lightness */
  --color-surface-subtle:   var(--gov-neutral-11);
  --color-surface-card:     oklch(1 0 0);
  --color-surface-elevated: oklch(1 0 0);
  --color-text-primary:     var(--gov-neutral-1);
  --color-text-secondary:   var(--gov-neutral-3);
  /* ...continue pattern: dark tier 1 maps to opposite end */
}
```

Primitives stay constant; **only semantic tier swaps**. Components never care which mode.

---

## 3. Typography — Vietnamese-hardened

Vietnamese stacks up to **three diacritics vertically** (`ế`, `ộ`, `ằ`), so English-tuned type scales collapse. Every typography rule here is bent toward not crushing stacked marks.

**Reference:** [Vietnamese Typography — Type Recommendations](https://vietnamesetypography.com/type-recommendations/) & [Diacritical Details](https://vietnamesetypography.com/diacritical-details/) (Donny Truong — canonical).

### Font stack

```css
--font-sans:  "Inter", "Inter Variable", system-ui, -apple-system, sans-serif;
--font-serif: "Source Serif 4", "Source Serif 4 Variable", Georgia, serif;
--font-mono:  "JetBrains Mono", "JetBrains Mono Variable", ui-monospace, "SF Mono", monospace;
```

Inter and Source Serif 4 both ship full Vietnamese coverage and were designed for multilingual typesetting.

### Global font feature settings

Apply globally to `html` or `body` so every descendant inherits — BUT use `font-variant-numeric` (cascading) for tabular, not `font-feature-settings: "tnum"` (replacing).

```css
html {
  font-family: var(--font-sans);
  font-feature-settings: "kern", "ss01", "ss03", "cv11", "zero";
  /* ss01 = disambiguated i/l/1 (mandatory for gov forms)
     ss03 = stylistic set 3 (rounded corners for lower-case)
     cv11 = single-story a
     zero = slashed zero */
  font-optical-sizing: auto;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

table, .tabular, td, .timestamp, .money, .compliance-score {
  font-variant-numeric: tabular-nums;  /* cascades, unlike "tnum" feature */
}
```

**Pitfall:** never set `font-feature-settings: "tnum"` on a descendant — it *replaces* the inherited feature list, silently dropping `kern`, `ss01`, `cv11`. Use `font-variant-numeric` which cascades independently. [Typotheque writeup](https://www.typotheque.com/articles/opentype-features-in-css).

### Scale selection

GovFlow ships **two parallel scales** for different surface types:

| Scale | Ratio | Use for |
|---|---|---|
| **Dashboard** | Major Second (1.125) | Internal workspace — Intake, Compliance, Inbox, Leadership Dashboard, Security Console, Agent Trace. Compact, data-dense. |
| **Reading** | Minor Third (1.2) | Legal document viewer, statute text, long-form narrative, citizen-facing help docs. Generous, readable at distance. |

Switch at the page-template level (`<article class="reading-scale">`), never at the component level. Minor Second (1.067) is too flat for legal hierarchy; Perfect Fourth (1.333) is too expensive for dense dashboards.

### Dashboard scale

```css
--text-meta:    11px;   /* timestamps, audit tags */
--text-caption: 12px;   /* helper text, micro copy */
--text-small:   13px;   /* labels, dense table cells */
--text-body:    14px;   /* default body — VN dashboard */
--text-emph:    16px;   /* emphasized body */
--text-sub:     18px;   /* subheadings in cards */
--text-title:   20px;   /* card titles */
--text-h3:      24px;   /* section headers */
--text-h2:      28px;   /* page headers */
--text-h1:      32px;   /* hero headlines */
--text-display: 40px;
--text-mega:    48px;
```

### Reading scale

```css
--text-legal-body:    16px;  /* statute body text */
--text-legal-emph:    18px;  /* emphasized quote */
--text-legal-sub:     22px;  /* article header */
--text-legal-h3:      26px;  /* section */
--text-legal-h2:      32px;  /* chapter */
--text-legal-h1:      40px;  /* title */
```

### Line-height — CRITICAL for Vietnamese

```css
--lh-vn-body:     1.65;   /* body copy — NOT 1.5, stacked diacritics collide */
--lh-vn-heading:  1.25;   /* minimum for headings */
--lh-vn-legal:    1.75;   /* legal documents, long-form reading */
--lh-tight:       1.15;   /* tabular data rows only */
--lh-mono:        1.5;    /* code blocks, Gremlin queries */
```

Default `line-height` on body is **1.65**. Going below 1.5 causes `ế` descenders to collide with ascenders of the next line. Going below 1.25 on headings causes stacked diacritics to overlap with the line above.

### Letter-spacing

```css
--tracking-tight:   -0.01em;  /* max negative — cap for VN headings */
--tracking-normal:   0;       /* default */
--tracking-wide:     0.02em;  /* labels, all-caps */
--tracking-widest:   0.08em;  /* classification banners, section eyebrows */
```

**Pitfall:** Linear/Stripe use aggressive `-0.025em` tracking for display text. **Do not copy this for Vietnamese.** Negative tracking crushes diacritic stacks into adjacent glyphs. Cap at `-0.01em`.

### Canonical Vietnamese test paragraph

Use this exact paragraph to visually verify every typography change. It contains stacked diacritics (ẩ, ệ, ể, ằ, ỡ), mixed-script (Arabic numerals + Vietnamese), tabular figures (legal references), and line-length conditions that expose kerning issues. Render it at 14/23 and 16/26 and 24/30 — if any combination fails (diacritic collision, baseline jitter, misaligned legal refs), the type scale is wrong.

```
Căn cứ Nghị định số 136/2020/NĐ-CP ngày 24/11/2020 của Chính phủ về việc
quy định chi tiết một số điều và biện pháp thi hành Luật Phòng cháy và
chữa cháy, Luật sửa đổi, bổ sung một số điều của Luật Phòng cháy và chữa
cháy; Điều 13 khoản 2 điểm b quy định công trình có tổng diện tích sàn
từ 300m² trở lên tại khu công nghiệp, khu chế xuất, cụm công nghiệp
thuộc danh mục phải thẩm duyệt thiết kế về phòng cháy và chữa cháy. Hồ
sơ của ông Nguyễn Văn M*** gồm 500m² tại Khu công nghiệp Mỹ Phước,
tỉnh Bình Dương, thuộc trường hợp quy định tại điểm b nêu trên. Đề nghị
chủ hồ sơ liên hệ Phòng Cảnh sát Phòng cháy chữa cháy và Cứu nạn cứu hộ
Công an tỉnh Bình Dương để được hướng dẫn thẩm duyệt. Thời gian xử lý
dự kiến: 10 ngày làm việc kể từ ngày nhận đủ hồ sơ.
```

**Visual checks:**
1. `ẩ` in "điểm" does not collide with descenders of line above
2. `ệ` in "nghiệp" has breathing room
3. `ằ` in "bằng" (if present) sits cleanly
4. `300m²` superscript 2 aligns to cap height, not baseline
5. `24/11/2020` and `500m²` use tabular figures (all digits same width)
6. Line length averages 65-75 characters per line at the reading scale (Minor Third)
7. No orphans (single-word last lines) in the first screenful
8. Inter `ss01` renders disambiguated `I`/`l`/`1` — look at "Luật" and "136" to verify

**Rendering target per composed class:**

| Class | Expected metrics | Test |
|---|---|---|
| `.text-body-14` | 14px / 23.1px lh (= 1.65) / weight 400 / VN features | dashboard use |
| `.text-body-16` | 16px / 26.4px lh / weight 400 | emphasized body |
| `.text-legal-16` | 16px / 28px lh (= 1.75) / Source Serif 4 / weight 400 | legal body (higher lh) |
| `.text-heading-24` | 24px / 30px lh (= 1.25) / weight 600 / `-0.008em` tracking | section header (tight lh but stacked diacritics must not collide) |

**Failure patterns to watch for:**
- ❌ "Phòng cháy chữa cháy" — if `ò`, `á`, `ữ`, `á` stack awkwardly, tracking is too tight
- ❌ "thẩm duyệt" — if `ẩ` and `ệ` touch the line above, line-height is too tight (not 1.65)
- ❌ "Mỹ Phước" — if `ỹ` and `ư` look like `y` and `u`, the font variant is wrong (not Inter VN subset)
- ❌ Tabular numbers `136/2020` — if digits don't align vertically in a column, `font-variant-numeric: tabular-nums` not applied

**Reference rendering (what "right" looks like):** open the test paragraph in Google Docs with Inter 14/23 enabled — that's the baseline. Screen recordings of this paragraph should be saved as `frontend/test/typography-reference.png` for future visual regression testing.

### Composed text classes

Bundle size + line-height + tracking + weight + features (Geist pattern). Components reference these, never raw sizes:

```css
.text-meta-11       { font-size: 11px; line-height: 1.45; letter-spacing: 0.02em; font-weight: 500; color: var(--color-text-muted); }
.text-caption-12    { font-size: 12px; line-height: 1.5;  font-weight: 500; color: var(--color-text-secondary); }
.text-label-13-mono { font-size: 13px; line-height: 1.4;  font-family: var(--font-mono); font-weight: 500; }
.text-label-13      { font-size: 13px; line-height: 1.5;  font-weight: 500; letter-spacing: 0.01em; }
.text-body-14       { font-size: 14px; line-height: 1.65; font-weight: 400; }
.text-body-14-emph  { font-size: 14px; line-height: 1.65; font-weight: 500; }
.text-body-16       { font-size: 16px; line-height: 1.65; font-weight: 400; }
.text-legal-16      { font-size: 16px; line-height: 1.75; font-family: var(--font-serif); font-weight: 400; }
.text-title-20      { font-size: 20px; line-height: 1.3;  font-weight: 600; letter-spacing: -0.005em; }
.text-heading-24    { font-size: 24px; line-height: 1.25; font-weight: 600; letter-spacing: -0.008em; }
.text-heading-28    { font-size: 28px; line-height: 1.2;  font-weight: 650; letter-spacing: -0.01em; }
.text-hero-40       { font-size: 40px; line-height: 1.15; font-weight: 700; letter-spacing: -0.01em; }
.text-mono-13       { font-size: 13px; line-height: 1.5;  font-family: var(--font-mono); }
```

Developers never hand-tune a `<h3>`. They pick the closest composed class.

---

## 4. Motion — Material 3 duration + easing scale

**Default posture:** tween + emphasized ease for system-driven transitions (modals, toasts, WS events). Spring ONLY for direct manipulation (drag, reorder). `bounce ≤ 0.1` for interactive, `0` everywhere else — court-serious brands don't wobble.

**Reference:** [Material 3 — Easing and duration tokens](https://m3.material.io/styles/motion/easing-and-duration/tokens-specs).

### Duration tokens

```css
--duration-short-1:      50ms;   /* state changes: hover, focus ring appear */
--duration-short-2:     100ms;   /* small enter/exit: icon morph, check mark */
--duration-short-3:     150ms;   /* checkbox, switch, toggle */
--duration-short-4:     200ms;   /* default UI transition, color change */
--duration-medium-1:    250ms;   /* card enter, list item slide */
--duration-medium-2:    300ms;   /* dialog, sheet, slide panel */
--duration-medium-3:    350ms;
--duration-medium-4:    400ms;   /* emphasis: agent step glow, edge draw */
--duration-long-1:      450ms;   /* full-page transition */
--duration-long-2:      500ms;   /* graph edge dashoffset draw */
--duration-long-3:      550ms;
--duration-long-4:      600ms;   /* pulse cycle, counter animate on hover */
--duration-xl-1:        700ms;   /* onboarding only — never interactive */
```

### Easing tokens

```css
--ease-linear:       linear;
--ease-standard:     cubic-bezier(0.2, 0, 0, 1);         /* default in/out */
--ease-emphasized:   cubic-bezier(0.3, 0, 0, 1);         /* default for enters */
--ease-accelerate:   cubic-bezier(0.3, 0, 1, 1);         /* default for exits */
--ease-decelerate:   cubic-bezier(0, 0, 0, 1);           /* incoming */
--ease-spring-soft:  cubic-bezier(0.34, 1.2, 0.64, 1);   /* gentle bounce, ≤0.1 */
```

Use `--ease-emphasized` as the default unless you have a specific reason otherwise.

### Spring vs tween rule

**Tween** when the *system* is the actor: modal open, route change, toast enter, data refresh, graph node appear. These are the 90% case in gov tech.

**Spring** when the *user* is the actor: drag to reorder, swipe to dismiss, pinch to zoom, resize a panel. User's finger provides the physics reference — the spring tracks their gesture velocity.

In Framer Motion v12:

```tsx
// System actor — tween (default)
<motion.div
  initial={{ opacity: 0, y: -8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.25, ease: [0.3, 0, 0, 1] }}  // --ease-emphasized
/>

// User actor — duration-based spring (NOT react-spring presets — those don't exist in Motion v12)
<motion.div
  drag
  dragTransition={{ duration: 0.3, bounce: 0.1 }}
/>
```

**Never `bounce > 0.1`** on interactive; never `bounce > 0` on system transitions.

### Reduced motion — legal requirement

WCAG 2.2 AA is the 2026 legal minimum (US DOJ rule, EU EAA, UK PSBAR, Vietnam TCVN accessibility). Two-layer implementation:

1. **CSS media query** (catches everything):

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

2. **Framer Motion wrapper** at root:

```tsx
<MotionConfig reducedMotion="user">
  <App />
</MotionConfig>
```

Plus a per-user toggle in settings that overrides OS pref (some users enable OS reduce-motion but want app motion). Never *remove* motion entirely — replace `translate` transitions with opacity crossfade so users still get state-change feedback.

---

## 5. Elevation / shadow tokens

Heavy shadows are the #1 "student project" tell in graph UIs. Gov tech should use **barely-there** shadows. Borders do most of the work.

```css
--shadow-none:     none;
--shadow-subtle:   0 1px 2px 0 oklch(0 0 0 / 0.04);
--shadow-card:     0 1px 3px 0 oklch(0 0 0 / 0.06), 0 1px 2px -1px oklch(0 0 0 / 0.04);
--shadow-raised:   0 4px 6px -1px oklch(0 0 0 / 0.08), 0 2px 4px -2px oklch(0 0 0 / 0.04);
--shadow-popover:  0 10px 15px -3px oklch(0 0 0 / 0.10), 0 4px 6px -4px oklch(0 0 0 / 0.05);
--shadow-modal:    0 24px 48px -12px oklch(0 0 0 / 0.25);
--shadow-inset:    inset 0 1px 0 0 oklch(1 0 0 / 0.04);
```

**Rules:**
- **Graph nodes: `--shadow-subtle` or none.** Never `--shadow-raised` or above on React Flow nodes — reads as prototype.
- **Dark mode shadows use `oklch(0 0 0 / ...)` not `rgba(0,0,0,...)`** for P3 consistency.
- **Light mode shadows** use the same tokens (oklch(0 0 0) ≡ black in any color space) but may want slightly higher alpha values — TBD in light mode implementation.

---

## 6. Spacing + radius

### Spacing — 8px grid with 4px micro-adjustments

```css
--space-0:    0;
--space-0-5:  2px;
--space-1:    4px;
--space-1-5:  6px;
--space-2:    8px;   /* base grid unit */
--space-3:    12px;
--space-4:    16px;
--space-5:    20px;
--space-6:    24px;
--space-8:    32px;
--space-10:   40px;
--space-12:   48px;
--space-16:   64px;
--space-20:   80px;
--space-24:   96px;
```

**Rule:** node padding in graph viz ≥ `--space-3` (12px) inner. Cramped nodes read as prototype.

### Border radius

```css
--radius-none:   0;
--radius-sm:     2px;
--radius-md:     4px;
--radius-lg:     6px;
--radius-xl:     8px;   /* cards, buttons default */
--radius-2xl:   12px;   /* modals, large cards */
--radius-3xl:   16px;
--radius-full:  9999px; /* pills, badges */
```

---

## 7. Focus ring

Non-negotiable per WCAG 2.2. Visible on every interactive element via `:focus-visible` (not `:focus` — keyboard users only, not click users).

```css
--focus-ring-width:  3px;
--focus-ring-offset: 2px;
--focus-ring-color:  var(--color-border-focus);
--focus-ring: 0 0 0 var(--focus-ring-width) var(--focus-ring-color);
```

Applied via utility:

```css
.focus-ring:focus-visible {
  outline: none;
  box-shadow: 0 0 0 var(--focus-ring-offset) var(--color-surface-page),
              0 0 0 calc(var(--focus-ring-offset) + var(--focus-ring-width)) var(--focus-ring-color);
}
```

**3px width is non-negotiable** — below 3px fails AA for keyboard accessibility. GOV.UK uses 3px yellow-on-black; you can tune color, but keep the thickness.

---

## 8. How to use these tokens

### In Tailwind v4 (CSS-first `@theme`)

```css
/* tokens/color.css — primitives */
@theme {
  --color-surface-page: var(--gov-neutral-1);
  --color-text-primary: var(--gov-neutral-12);
  /* ... Tailwind auto-generates utilities: bg-surface-page, text-primary, etc */
}
```

### In a component

```tsx
// RIGHT — semantic reference
<button className="bg-action-solid text-on-accent hover:bg-action-hover">
  Phê duyệt
</button>

// WRONG — primitive reference (breaks retheming)
<button className="bg-[oklch(0.55_0.195_255)] text-white hover:bg-[oklch(0.60_0.190_255)]">
  Phê duyệt
</button>
```

### In Framer Motion

```tsx
import { motion } from "framer-motion";

// RIGHT — duration + easing tokens via CSS vars
const slideUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: {
    duration: 0.25,
    ease: [0.3, 0, 0, 1],  // --ease-emphasized
  },
};

// WRONG — hand-tuned inline
const slideUp = {
  transition: { duration: 0.237, ease: "easeOut" },
};
```

For Motion components that can't read CSS vars directly, expose the tokens as a JS object in `frontend/lib/motion.ts`:

```ts
export const motionTokens = {
  duration: {
    short1: 0.05, short2: 0.1, short3: 0.15, short4: 0.2,
    medium1: 0.25, medium2: 0.3, medium3: 0.35, medium4: 0.4,
    long1: 0.45, long2: 0.5, long3: 0.55, long4: 0.6,
  },
  ease: {
    standard:    [0.2, 0, 0, 1],
    emphasized:  [0.3, 0, 0, 1],
    accelerate:  [0.3, 0, 1, 1],
    decelerate:  [0, 0, 0, 1],
  },
};
```

---

## 9. Verification

Build-time lint enforces:

1. **No raw hex** in `frontend/app/` or `frontend/components/` outside `frontend/styles/tokens/`.
2. **No inline `transition: { duration: 0.XXX }`** — must reference `motionTokens`.
3. **Every `--color-*` semantic has a paired `-fg`/`-text`** with AA contrast (≥ 4.5:1).
4. **OKLCH primitive generator** runs on CI to verify ramps are perceptually matched.

Run before commit:

```bash
pnpm tokens:lint    # check no raw hex
pnpm tokens:contrast # check all semantic pairs
pnpm tokens:gen     # regenerate alpha variants
```

---

## 10. When to add / change tokens

- **New primitive ramp** (e.g. a brand-adjacent accent): get team review; adding a ramp is a design decision, not an engineering one.
- **New semantic token:** OK to add when a component needs a role not covered. Name by role, not color.
- **Override primitive value:** only when brand refresh happens. Never to fix a single component — that's a component token.
- **Motion/duration:** never hand-tune. If an animation needs a duration not in the scale, either pick the nearest scale step or propose extending the scale team-wide.

---

## Appendix — Cheat sheet

| Need | Use |
|---|---|
| Primary button bg | `bg-action-solid` |
| Primary button hover | `hover:bg-action-hover` |
| Body text | `.text-body-14` (dashboard) or `.text-legal-16` (reading) |
| Card bg | `bg-surface-card` |
| Card border | `border-border-default` |
| Approved badge | `bg-status-success-bg text-status-success-fg` |
| Gap callout | `bg-status-warning-bg text-status-warning-fg border-status-warning-border` |
| Denied toast | `bg-status-danger-solid text-on-accent` |
| Classification banner | `bg-class-confid-banner text-class-confid-text` |
| Redaction | `<span class="bg-redact-bar">` (solid bar) |
| Hover transition | `transition-colors duration-200 ease-[cubic-bezier(0.3,0,0,1)]` |
| Card enter animation | `duration-medium-1` + `--ease-emphasized` |
| Graph edge draw | `duration-long-2` + `--ease-standard` |
