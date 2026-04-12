# Design Theme — Visual identity & mindset

## Theme statement

> **"The OS of public administration — serious, transparent, accessible."**

GovFlow là công cụ cho cơ quan nhà nước. Không phải consumer app. Không flashy, không neon, không gimmick. Nhưng cũng không đơn điệu như phần mềm gov cũ. Sự kết hợp cần đạt: **nghiêm túc như tòa án, hiện đại như Linear/Vercel, thân thiện như Arcade**.

## References

- **Linear** (linear.app) — layering, spacing, motion subtlety
- **Vercel dashboard** — hierarchy, dark mode excellence
- **Arcade** (arc.net) — micro-interactions
- **Stripe dashboard** — data visualization
- **Raycast** — command palette UX
- **Notion** — content density without overwhelming

## Visual language

### Color palette

**Primary / brand**
- `--bg-primary: #0B1220` (dark navy — "serious state")
- `--bg-secondary: #0F172A`
- `--bg-tertiary: #1E293B`
- `--text-primary: #F8FAFC`
- `--text-secondary: #94A3B8`
- `--brand-blue: #2563EB` (trust + action)
- `--brand-blue-hover: #1D4ED8`

**Classification colors** (critical — visual hierarchy)
- `--unclassified: #10B981` (emerald — safe / public)
- `--confidential: #F59E0B` (amber — attention)
- `--secret: #F97316` (orange — caution)
- `--top-secret: #DC2626` (red — danger)

**Semantic**
- `--success: #10B981`
- `--warning: #F59E0B`
- `--destructive: #DC2626`
- `--info: #3B82F6`
- `--compliance-score-green: #10B981` (>= 90%)
- `--compliance-score-yellow: #F59E0B` (70–89%)
- `--compliance-score-red: #DC2626` (< 70%)

**Graph node colors** (React Flow / Cytoscape)
- Case nodes: blue
- Document: gray
- Law / Article: purple
- TTHCSpec: teal
- Organization: cyan
- Gap: amber
- Decision: green/red
- AgentStep: small dots with agent color
- AuditEvent: small red dots

### Typography

- **UI text:** `Inter` (400, 500, 600, 700)
- **Document viewer:** `Source Serif 4` (for reading legal text — matches Vietnamese government document feel)
- **Mono:** `JetBrains Mono` (for code + Gremlin query + graph ids)

Scale:
- `text-xs: 12px` — meta info
- `text-sm: 14px` — body
- `text-base: 16px` — default
- `text-lg: 18px` — subheadings
- `text-xl: 20px` — section headers
- `text-2xl: 24px` — page headers
- `text-4xl: 36px` — hero headlines (Citizen Portal)

### Spacing

8px grid. All padding, margin, gap in multiples of 4px. Never arbitrary values.

### Elevation

- Cards have `shadow-sm` by default, `shadow-md` on hover
- Modals have `shadow-2xl` with backdrop blur
- Graph viewer has subtle inner shadow to suggest "canvas"

## Motion language

**Principle:** Every animation has purpose. Never animate for flair. Motion should guide attention or explain causality.

**Guidelines:**
- **Duration:** 150ms (micro), 250ms (default), 400ms (emphasis), 600ms (page transition)
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-quart for most things)
- **Library:** Framer Motion for React; CSS transitions for simple hovers

**Key animations:**
1. **Agent trace node appearance** — `fade-in + scale(0.9→1.0)` + subtle glow
2. **Edge draw** — `stroke-dashoffset` animation, 400ms
3. **Routing "fly"** — card animates from intake to department inbox (600ms)
4. **Permission denied shake** — `x:[-4,4,-4,4,0]` in 200ms, red pulse
5. **Mask dissolve (Scene C)** — solid-bar redaction unmount + revealed content crossfade (opacity 0→1, 250ms). **NOT blur** — blur is cryptographically recoverable and reads as consumer soft-focus. See [`../04-ux/design-system.md` Redaction section](../04-ux/design-system.md) for the full pattern.
6. **SLA countdown** — progress bar desaturate as time runs out
7. **Success confirmation** — checkmark stroke animation + green pulse

**Avoid:** parallax, aggressive slides, rotations, bounce (too playful for gov context).

## Icon system

- **Library:** Lucide React (simple, consistent, open source)
- **Size:** 16px (inline), 20px (buttons), 24px (headers), 32px (feature)
- **Weight:** `stroke-width: 1.5`

Custom icons cho classification badges (4 levels) — simple shapes with clear color differentiation.

## Components (shadcn/ui customized)

Base: shadcn/ui. Customize for gov context:

- **Button:** add `variant="destructive-confirm"` for high-stakes actions (requires 2-step confirm)
- **Badge:** add classification variants (4 colors)
- **Card:** add `variant="case"` with SLA indicator + compliance score slot
- **Dialog:** add blur backdrop + escape confirmation for forms with changes
- **Table:** add sticky header + column sort + row hover + selection
- **Toast:** 4 variants (success/warning/destructive/info) with icons

## Layout patterns

### Citizen Portal (public)
```
┌────────────────────────────────────────────┐
│  [logo] Cổng GovFlow    [login via VNeID] │
├────────────────────────────────────────────┤
│                                             │
│   Hồ sơ của bạn                            │
│   [big search by mã hồ sơ]                 │
│                                             │
│   Hoặc:                                     │
│   [Nộp hồ sơ mới]  [Xem hướng dẫn TTHC]   │
│                                             │
├────────────────────────────────────────────┤
│   Các TTHC phổ biến: CPXD | ĐKKD | ...    │
└────────────────────────────────────────────┘
```

### Internal Workspace
```
┌─────┬──────────────────────────────────────┐
│ nav │  Top bar: search (⌘K), user, bell   │
├─────┼──────────────────────────────────────┤
│ • Inbox                                      │
│ • Comp.│    [ main content area ]          │
│ • Docs │                                     │
│ • Sec. │                                     │
│ • Admin│                                     │
│        │                                     │
└─────┴──────────────────────────────────────┘
```

## Data density rules

- **Citizen Portal:** low density, big type, lots of whitespace. Non-technical user.
- **Chuyên viên Workspace:** medium density, balanced. Information dense but readable.
- **Leadership Dashboard:** medium-low density, big charts + headline numbers. Quick scan.
- **Security Console:** high density, table-heavy, log-style. Technical users, need to see a lot at once.
- **Agent Trace Viewer:** variable — collapse by default, expand on demand.

## Dark mode + light mode

Build both from day 1. Most gov users might prefer light (familiar), but dark mode is polished differentiator. Default light for Citizen Portal (accessibility), default dark for Security Console (forensic feel).

## Accessibility

- **WCAG AA** minimum, AAA for text color contrast where possible
- **Keyboard navigation** — everything reachable via tab + ⌘K command palette
- **Screen reader** — proper ARIA labels, especially for dynamic agent trace
- **Reduced motion** — respect `prefers-reduced-motion` (disable non-essential animations)
- **Font size** — zoom-friendly, no fixed px body font

## Branding elements

- **Logo idea:** stylized graph node + Vietnamese element (star from national flag, or lotus silhouette). Simple, mono, works on any background. Build this day 1.
- **Product name:** GovFlow (Vietnamese: "Dòng chảy Hành chính công")
- **Tagline:** "Agentic AI for Vietnamese Public Services" (EN) / "Trí tuệ nhân tạo cho dịch vụ công Việt Nam" (VN)

## Voice & tone

- **For citizens:** friendly, clear, plain Vietnamese. Avoid jargon. Example: "Hồ sơ của bạn cần thêm 1 giấy tờ. Nhấn đây để xem chi tiết."
- **For civil servants:** professional, structured. Example: "Compliance check: 94%. 1 thành phần thiếu. Xem chi tiết."
- **For leadership:** executive, data-forward. Example: "3 hồ sơ gần overdue. SLA hit rate tuần này: 87%."
- **For security:** forensic, precise. Example: "User ID XYZ attempted to access doc DEF at 14:23. Clearance: Confidential. Doc classification: Secret. Access denied. Audit ID: 12345."

## Demo polish checklist

Mỗi màn hình trước khi ship phải pass checklist:
- [ ] Có empty state
- [ ] Có loading state (skeleton, not spinner)
- [ ] Có error state
- [ ] Có focus ring cho keyboard nav
- [ ] Hover states cho mọi interactive element
- [ ] Responsive ít nhất 1440px (demo laptop) và 1920px (projector)
- [ ] Dark mode tested
- [ ] Animations smooth ở 60fps
- [ ] Vietnamese text render đúng font
- [ ] Không có lorem ipsum — tất cả content thật
