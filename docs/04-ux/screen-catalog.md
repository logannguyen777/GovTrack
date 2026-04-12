# Screen Catalog — 8 màn hình chính

Text-based wireframes + functional spec cho từng screen. Dùng để build theo đúng thứ tự theo [`../08-execution/daily-plan.md`](../08-execution/daily-plan.md).

---

## 1. Citizen Portal — Public

### Purpose
Mặt tiền công khai cho công dân / doanh nghiệp. Simple, friendly, accessible. Light theme default.

### Routes
- `/` — home (search + submit)
- `/cases/[code]` — track by case code
- `/tthc` — browse TTHCs
- `/tthc/[code]` — TTHC detail + guided wizard
- `/submit/[tthc_code]` — upload bundle for specific TTHC

### Key features

**Home page:**
```
┌─────────────────────────────────────────────┐
│ [logo] GovFlow          [Đăng nhập VNeID]  │
├─────────────────────────────────────────────┤
│                                              │
│    Thủ tục hành chính công thông minh       │
│    Nhanh hơn. Minh bạch hơn. Dễ hiểu hơn.  │
│                                              │
│    ┌──────────────────────────────────────┐ │
│    │ 🔍 Tra cứu bằng mã hồ sơ            │ │
│    └──────────────────────────────────────┘ │
│                                              │
│    Hoặc bắt đầu hồ sơ mới:                  │
│                                              │
│    ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
│    │ Cấp  │ │ GCN  │ │ ĐK   │ │ Lý   │     │
│    │ phép │ │ QSDĐ │ │ kinh │ │ lịch │     │
│    │ XD   │ │      │ │doanh │ │ TP   │     │
│    └──────┘ └──────┘ └──────┘ └──────┘     │
│                                              │
│    [Xem tất cả TTHC]                        │
│                                              │
├─────────────────────────────────────────────┤
│  Hôm nay: 1,247 hồ sơ đang xử lý            │
│  SLA trung bình tuần này: 1.8 ngày          │
│  (thấp hơn 95% so với trước)                │
└─────────────────────────────────────────────┘
```

**Case tracking page (`/cases/[code]`):**
```
┌─────────────────────────────────────────────┐
│ ← Trang chủ                                  │
├─────────────────────────────────────────────┤
│                                              │
│  Hồ sơ: C-20260412-0001                     │
│  Cấp giấy phép xây dựng                     │
│                                              │
│  Trạng thái: 🟡 Chờ bổ sung giấy tờ          │
│                                              │
│  Timeline:                                   │
│  ✓ 12/04 14:30  Nộp hồ sơ                   │
│  ✓ 12/04 14:30  Tiếp nhận                   │
│  ✓ 12/04 14:31  Phân tích                   │
│  ⚠ 12/04 14:32  Thiếu giấy tờ               │
│  ⏳ Chờ bạn bổ sung                          │
│                                              │
│  ┌─────────────────────────────────────┐   │
│  │ Bạn cần bổ sung:                     │   │
│  │ Văn bản thẩm duyệt PCCC              │   │
│  │                                       │   │
│  │ Lý do: Công trình 500m² tại KCN      │   │
│  │ Mỹ Phước thuộc diện phải thẩm duyệt │   │
│  │ PCCC theo NĐ 136/2020 Điều 13.       │   │
│  │                                       │   │
│  │ Nơi nhận: Phòng Cảnh sát PCCC        │   │
│  │ Công an tỉnh Bình Dương              │   │
│  │                                       │   │
│  │ [Xem hướng dẫn chi tiết]             │   │
│  │ [📎 Upload bổ sung ở đây]            │   │
│  └─────────────────────────────────────┘   │
│                                              │
│  Ước tính hoàn tất: 3–5 ngày sau khi        │
│  bổ sung giấy tờ                             │
└─────────────────────────────────────────────┘
```

**Submit wizard:**
- Step 1: Select TTHC + VNeID authenticate
- Step 2: Upload required documents (with preview)
- Step 3: Review + submit
- Step 4: Confirmation + case code

### Loading / skeleton

**Home page:** SSR full render (SEO-critical). No skeleton needed for the hero — TTHC buttons and search bar appear immediately. Live stats footer ("1,247 hồ sơ đang xử lý") renders with count at 0, then counter-animates to real value over 800ms via `<AnimatedCounter>` when data arrives from `/api/stats/public`.

**Case tracking page (`/cases/[code]`):**

```
┌─────────────────────────────────────────────┐
│ ← Trang chủ                                  │
├─────────────────────────────────────────────┤
│                                              │
│  Hồ sơ: ▒▒▒▒▒▒▒▒▒▒▒▒▒▒                     │
│  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒                        │
│                                              │
│  ▒▒▒▒▒▒▒▒▒▒▒▒▒                              │
│                                              │
│  Timeline:                                   │
│  ○ ▒▒▒▒▒▒▒▒▒▒                               │
│  ○ ▒▒▒▒▒▒▒▒▒▒                               │
│  ○ ▒▒▒▒▒▒▒▒▒▒                               │
│                                              │
│  ┌─────────────────────────────────────┐   │
│  │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒               │   │
│  │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒               │   │
│  │ ▒▒▒▒▒▒▒▒▒                            │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

SSR renders the case title + timeline shell from cached summary; detailed gap notice + legal refs stream in via CSR fetch + WS subscribe for live updates.

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| Case not found (invalid code) | "Không tìm thấy hồ sơ này. Vui lòng kiểm tra lại mã." + [Về trang chủ] + [Liên hệ hỗ trợ] | — |
| Case exists but user not authenticated | Show "Vui lòng đăng nhập VNeID để xem chi tiết hồ sơ" + login button | VNeID redirect |
| WS connection fails (live updates unavailable) | Yellow banner top "Cập nhật trạng thái tự động không khả dụng. [Làm mới]" — timeline still shows cached state from SSR | Manual refresh or auto-retry every 60s |
| Document download fails | Inline "Không thể tải file. [Thử lại] hoặc liên hệ bộ phận hỗ trợ" | Retry or contact |
| Offline (mobile) | "Không có kết nối mạng. Trạng thái cuối cùng: [cached state from SSR]" + retry on reconnect | Auto-retry on back online |
| Bad signal mid-upload | Progress bar pauses + "Mạng yếu, đang chờ..." + auto-resume | Auto-resume, no user action |

### Mobile view (Scene 4 hero)

> Scene 4 (1:05-1:20) shows anh Minh's phone receiving push notification and opening tracking page. This must be specced as carefully as the desktop view — it's the citizen's primary interface.

**Responsive breakpoint:** `sm: 640px` and below. Citizen Portal uses light theme by default on mobile.

**Mobile tracking page layout (iPhone 13 mini, 375×812):**

```
┌────────────────────────┐
│ [≡] GovFlow          🔔│ ← sticky header (h=56px)
├────────────────────────┤
│                         │
│ Hồ sơ: C-20260412-0001 │
│ Cấp giấy phép XD       │
│                         │
│ 🟡 Chờ bổ sung giấy tờ │
│                         │
│ ─── Timeline ───        │
│ ✓ 14:30  Nộp hồ sơ     │
│ ✓ 14:30  Tiếp nhận     │
│ ✓ 14:31  Phân tích     │
│ ⚠ 14:32  Thiếu giấy tờ │
│ ⏳       Chờ bạn bổ sung│
│                         │
│ ┌────────────────────┐ │
│ │ Bạn cần bổ sung:   │ │
│ │ Văn bản thẩm duyệt │ │
│ │ PCCC               │ │
│ │                     │ │
│ │ ▼ Lý do            │ │
│ │ (collapse by default│ │
│ │  on mobile)        │ │
│ │                     │ │
│ │ 📍 Nơi nhận:        │ │
│ │ Phòng CS PCCC       │ │
│ │ [Mở bản đồ] →       │ │
│ │                     │ │
│ │ [📷 Chụp và upload]│ │ ← BIG touch button 56px
│ └────────────────────┘ │
│                         │
│ Ước tính: 3-5 ngày sau  │
│ khi bổ sung             │
└────────────────────────┘
  │ home indicator      │
  └─────────────────────┘
```

**Touch interaction rules:**
- All interactive touch targets ≥ 48×48px (WCAG AA)
- Primary action ("Chụp và upload") as a full-width button 56px tall
- Gap reason collapsed by default on mobile (tap to expand) — avoids scrolling past the CTA
- Swipe-down to refresh (pull-to-refresh pattern)
- Tap legal citation opens modal bottom sheet (not full-screen nav)
- Long-press on case code copies to clipboard + haptic feedback
- Map button opens OS maps app directly (no embedded map on mobile — saves bandwidth)

**Typography on mobile:**
- Body text stays at `--text-body-14` (14px) NOT scaled down — Vietnamese diacritics already tight at 14px, any smaller risks readability
- Headings one step smaller than desktop: `--text-heading-24` becomes `--text-title-20` on mobile
- Line-height stays at `--lh-vn-body: 1.65` (non-negotiable for Vietnamese)

**Push notification format** (Firebase FCM / Zalo OA):
- **Title:** `GovFlow: Hồ sơ cần bổ sung`
- **Body:** `C-20260412-0001 thiếu Văn bản thẩm duyệt PCCC. Nhấn để xem.`
- **Icon:** GovFlow logo
- **Click action:** deep link to `/cases/C-20260412-0001`
- **Sound:** default system notification sound (do NOT use custom — feels spam-y)
- **Priority:** high for gap-found, normal for status updates

### Scene 4 choreography — Citizen feedback loop (1:05 → 1:20)

> Mobile-focused. This is the second choreography table for Citizen Portal — covers only the push notification + tracking page reveal for Scene 4. Links to [demo-video-storyboard.md Scene 4](../07-pitch/demo-video-storyboard.md).

| t | Phone state | UI event | Animation | Voiceover anchor |
|---|---|---|---|---|
| **0s (=1:05)** | Home screen, GovFlow not open | Push notification arrives | Phone vibrate (haptic) + notification banner slides down from top of phone frame 300ms `--ease-emphasized` | "Trong vòng 30 giây..." |
| **1.5s** | Push visible | Anh Minh reads: "GovFlow: Hồ sơ cần bổ sung. C-20260412-0001 thiếu Văn bản thẩm duyệt PCCC" | hold (2s) | — |
| **3s** | Tap notification | Phone unlock + GovFlow app launches | system launch anim (hold) | — |
| **5s** | GovFlow launching | Splash screen 500ms then auto-nav to `/cases/C-20260412-0001` | fade 250ms | — |
| **6s** | Tracking page empty frame | Header + timeline rows skeleton shimmer | shimmer 1.5s loop | — |
| **7s (=1:10)** | Tracking page hydrated | All 4 timeline items fade in (stagger 50ms), gap callout card slides up from bottom | stagger + slide-up 300ms | "...Drafter Agent sinh thông báo ngôn ngữ đời thường..." |
| **9s** | User scrolls to gap card | Gap card expands inline: "Vì công trình 500m² tại KCN Mỹ Phước..." | accordion 300ms | — |
| **12s (=1:17)** | User reads legal reason | Citation "NĐ 136/2020 Điều 13" highlighted as tap target | — (static) | "...biết ngay trên điện thoại..." |
| **14s (=1:19)** | User ready to act | Prominent "[📷 Chụp và upload]" CTA visible at bottom of card | — | "...không cần quay lại..." |
| **15s (=1:20)** | End Scene 4 | — | Scene 5 title card overlays | Scene 5 begins |

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §1](./artifact-inventory.md#1-citizen-portal-home--tracking):
- **MUST:** #25 Case status change, #6 Gap plain-language notice, #18 Published doc with QR, #11 SLA countdown, #26 Notification push
- **SHOULD:** #5 Classification badge, #8 Citation plain refs, #17 Draft "being prepared"
- **MAY:** #19 Decision state ("approved")

### States
- Not authenticated → shows VNeID login button
- No active cases → empty state with encouragement
- Active cases → list with status
- Error → retry + contact info (see error states above)

### Notifications
- Push (Firebase / Zalo OA)
- Email
- SMS (optional, cost)

### Tech notes
- SSR for SEO (TTHC info pages)
- Client-side rendering for authenticated views
- Progressive enhancement (works without JS for basics)

---

## 2. Intake UI — Cán bộ tiếp nhận

### Purpose
Chị Lan (Persona 2) tiếp công dân tại Bộ phận Một cửa. Scan bundle, auto-fill, check compliance trong 30 giây.

### Route
- `/intake`

### Layout
```
┌──────────────────────────────────────────────────────┐
│ [nav] ⌘K  [bell] [user: Chị Lan — Một cửa Sở XD]   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Tiếp nhận hồ sơ mới                                 │
│                                                       │
│  ┌─────────────────┐  ┌────────────────────────┐   │
│  │                  │  │ Thông tin hồ sơ         │   │
│  │  [Drop zone:     │  │                          │   │
│  │   drag & drop    │  │ Loại TTHC:               │   │
│  │   files here]    │  │ [Cấp phép XD  ▼]        │   │
│  │                  │  │ (auto suggested)         │   │
│  │  Or:             │  │                          │   │
│  │  [📷 Scan]       │  │ Chủ hồ sơ:               │   │
│  │  [📂 Browse]     │  │ [auto-filled from OCR]  │   │
│  │                  │  │                          │   │
│  │                  │  │ Mã hồ sơ: C-20260412-...│   │
│  │                  │  │                          │   │
│  │                  │  └────────────────────────┘   │
│  └─────────────────┘                                │
│                                                       │
│  ┌───────────────────────────────────────────────┐  │
│  │ Tài liệu đã upload:                           │  │
│  │ ✓ don_cpxd.pdf         → Đơn cấp phép XD      │  │
│  │ ✓ gcn_qsdd.jpg         → GCN QSDĐ             │  │
│  │ ✓ ban_ve.pdf           → Bản vẽ thiết kế      │  │
│  │ ✓ cam_ket_mt.pdf       → Cam kết môi trường   │  │
│  │ ✓ gp_kd.jpg            → Giấy phép KD         │  │
│  │ ⚠ Thiếu: Văn bản thẩm duyệt PCCC (cần)        │  │
│  │   [Báo công dân]                              │  │
│  └───────────────────────────────────────────────┘  │
│                                                       │
│  Compliance ████████████▒▒ 80% (thiếu 1 thành phần)  │
│                                                       │
│  [In biên nhận] [Tiếp nhận hồ sơ]                   │
└──────────────────────────────────────────────────────┘
```

### Real-time behavior
- Files upload directly to OSS (presigned URLs)
- Qwen3-VL processes each file in parallel
- As each file finishes OCR, its row updates live via WebSocket
- Compliance check runs after all files processed (~5 seconds)
- Missing items appear with warning + "Báo công dân" button

### Live reveal choreography (t=0 → t=15s)

> Mirrors [Agent Trace Viewer choreography table](#live-build-choreography-t0--t30s) structure for consistency. This is the **second-hero** screen — judges see it FIRST in Scene 2 (0:15-0:40), before the signature Agent Trace Viewer, so the first impression of "system artifacts appearing live" starts here.
>
> **Linked to:** [07-pitch/demo-video-storyboard.md Scene 2 Frames 2-3](../07-pitch/demo-video-storyboard.md) (0:20-0:40) + [artifact-inventory.md Table 3 Scene 2](./artifact-inventory.md#table-3--demo-video-timeline--artifact-first-reveal).

| t | Drop zone | File rows | Entity chips | Compliance bar | Info panel | Voiceover anchor |
|---|---|---|---|---|---|---|
| **0s** | Empty, "Kéo thả hoặc chọn tài liệu" | 0 | 0 | 0% (bar hidden) | TTHC dropdown empty, mã hồ sơ pre-generated "C-20260412-..." | Scene 2 Frame 1 @ 0:20 |
| **1s** | Files dropping — blue outline glow | 5 rows appearing with stagger 100ms, each with filename + upload progress bar + ⏳ spinner | 0 | 0% | Chủ hồ sơ: empty, awaiting OCR | — |
| **3s** | Drop zone idle (all files received) | 5 rows, each showing "OCR 40%..." with shimmer | 0 | 0% with amber "0/6 thành phần" | Empty | Scene 2 Frame 2 @ 0:23 |
| **4s** | hold | Row 1 (`don_cpxd.pdf`) ✓ → label "Đơn đề nghị" slides in next to filename | Row 1 gets 2 chips: "Loại hồ sơ: CPXD" + "Chủ hồ sơ: Nguyễn Văn M***" | **0% → 17%** counter animate (1 of 6 detected) | Chủ hồ sơ auto-fills: "Nguyễn Văn M***" (slide-in from right 250ms) | Scene 2 Frame 2 @ 0:24 |
| **6s** | hold | Row 2 (`gcn_qsdd.jpg`) ✓ → label "GCN QSDĐ" + small red dot icon for "có dấu đỏ" | Row 2 gets 3 chips: "Số GCN: AL 123456", "Diện tích: 500m²", "Vị trí: KCN Mỹ Phước" | **17% → 33%** | Info panel fills: `Diện tích: 500m², Vị trí: KCN Mỹ Phước KCN Bình Dương` | Scene 2 Frame 2 @ 0:28 |
| **8s** | hold | Row 3 (`ban_ve.pdf`) ✓ → label "Bản vẽ thiết kế" | Row 3 gets 2 chips: "Tỉ lệ 1:200", "Diện tích: 500m² (khớp)" | **33% → 50%** | — | — |
| **10s** | hold | Row 4 (`cam_ket_mt.pdf`) ✓ "Cam kết môi trường" + Row 5 (`gp_kd.jpg`) ✓ "Giấy phép KD" (parallel finish) | Rows 4 & 5 each get 2 chips | **50% → 83%** (both in one tick, smooth counter) | — | Scene 2 Frame 3 @ 0:32 |
| **12s** | hold | all 5 rows ✓, Compliance Agent fires | — | **83% → 80%** brief dip then stabilizes (Compliance recalculates) | — | Scene 2 Frame 3 @ 0:35 |
| **14s** | hold | + 1 amber row appears below: "⚠ Thiếu: Văn bản thẩm duyệt PCCC (cần)" with **amber shake** (NOT red — it's a gap, not an error) + "[Báo công dân]" button | — | **80% locked at amber** with label "thiếu 1 thành phần", bar stops counter animate | Info panel shows gap reason + legal citation "NĐ 136/2020 Điều 13.2.b" link | Scene 2 Frame 3 @ 0:38 |
| **15s** | hold | All settled | — | 80% amber | Info panel complete, Chị Lan hovers [Báo công dân] button | Scene 2 ends → Scene 3 begins @ 0:40 |

### Choreography rules

- **Camera fixed.** No pan, no zoom. Intake UI is a form, not a graph — viewport stays still.
- **Compliance bar counter animation** uses [design-tokens.md](./design-tokens.md) `--duration-medium-4: 400ms` + `--ease-emphasized` between each jump. Counter lerps smoothly, not tick-by-tick.
- **Entity chips stagger** 50ms per chip within a file row (3 chips = 150ms total reveal).
- **Gap row amber shake** is 200ms `x:[-3,3,-3,3,0]` — subtle, not alarming. This is a recoverable gap, not a terminal error.
- **Compliance bar brief dip** (83% → 80%) at t=12s is intentional: it shows the Compliance Agent "recalculating" when moving from file-presence check to content-completeness check. This is honest signal, not a bug. Don't smooth it out.
- **Sound:** if sound design is enabled (system pref respected), subtle chime on each ✓ (barely audible, 8KHz sine tone 80ms). NO chime on gap (silence is the signal).

### Initial state (t=0) details

```
┌──────────────────────────────────────────────────────┐
│ Tiếp nhận hồ sơ mới                                  │
│                                                       │
│ ┌─────────────────┐  ┌────────────────────────┐   │
│ │                  │  │ Thông tin hồ sơ         │   │
│ │  📂              │  │                          │   │
│ │  Kéo thả         │  │ Loại TTHC:               │   │
│ │  hoặc chọn       │  │ [Chọn TTHC ▼]           │   │
│ │  tài liệu        │  │                          │   │
│ │                  │  │ Chủ hồ sơ:               │   │
│ │  [📷 Scan]       │  │ (tự động điền từ OCR)   │   │
│ │  [📂 Browse]     │  │                          │   │
│ │                  │  │ Mã hồ sơ:                │   │
│ │                  │  │ C-20260412-0042          │   │
│ │                  │  │ (pre-generated)          │   │
│ └─────────────────┘  └────────────────────────┘   │
│                                                       │
│  (Tài liệu đã upload section hidden until t>0)       │
│                                                       │
│  (Compliance bar hidden until first file processed)  │
└──────────────────────────────────────────────────────┘
```

### Loading / skeleton

SSR renders shell (nav + page title + drop zone + info panel frame). Info panel has skeleton rows (`▒▒▒▒`) for fields that will auto-fill after OCR. No spinner anywhere — `<FileUploadDropZone>` shows its own idle state with call-to-action.

**Contradiction fix:** [design-system.md:375](./design-system.md#L375) mandates "skeleton (not spinner)" as mandatory state. Earlier drafts of this screen said "Processing (spinner on each row)" — that is now **corrected** to **row-level shimmer + per-file OCR progress chip**. Each row during t=1-12s shows a horizontal shimmer gradient + "OCR 40%..." chip, never a standalone spinner.

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| Upload failure | Row shows red "Upload failed" + [Retry] button, does NOT block other rows | Retry per-file |
| OCR failure on one file | Row turns amber, label shows "?" with [Retry OCR] button + [Manual label ▼] dropdown, compliance bar continues from remaining files | Retry or manual classify |
| OCR failure on all files | Full-page banner "Hệ thống OCR tạm không khả dụng. Tiếp tục thủ công?" | Fallback to manual labeling |
| Compliance check timeout | Compliance bar stays at last known % with spinner, banner "Đang kiểm tra compliance..." | Auto-retry at 30s, surface error at 60s |
| Citizen not present when gap found | "Báo công dân" button disabled, show tooltip "Công dân đã rời quầy. Dùng kênh SMS/Zalo" + fallback [Gửi SMS] | Fallback channel |

### Actions
- **Tiếp nhận hồ sơ** — creates Case, generates code, prints biên nhận
- **Báo công dân** — if missing items, notifies citizen immediately + saves partial
- **Hoãn tiếp nhận** — returns to citizen to gather missing items

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §2](./artifact-inventory.md#2-intake-ui):
- **MUST:** #1 OCR progress, #2 Document label, #3 ExtractedEntity chips, #4 TTHC classification auto-fill, #10 Compliance score bar, #6 Gap vertex alert
- **SHOULD:** #5 Classification preview, #11 SLA countdown post-intake
- **MAY:** #26 Notification confirmation

### States
- Empty (no files yet) — initial state above
- Uploading (progress bars per file)
- Processing (row-level shimmer + per-file OCR progress chip — **NOT spinner**)
- Complete (all rows ✓)
- Partial (some missing, amber shake on gap row — NOT error)
- Error (red with retry — see error states table above)

---

## 3. Agent Trace Viewer — THE signature screen

### Purpose
Signature demo feature. Visualize Context Graph growth in realtime as agents process a case. This is where judges will say "wow".

### Route
- `/cases/[id]/trace`

### Layout
```
┌──────────────────────────────────────────────────────┐
│ [nav] ← C-20260412-0001                              │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌───────────────┐  ┌──────────────────────────┐   │
│  │ Agent timeline │  │ Context Graph (live)     │   │
│  │                │  │                           │   │
│  │ ● Planner      │  │    [React Flow canvas]   │   │
│  │ │              │  │                           │   │
│  │ ● DocAnalyzer  │  │    Case                   │   │
│  │ │              │  │    ├── Bundle             │   │
│  │ ● SecurityOff  │  │    │   ├── Doc1 (gcn)    │   │
│  │ │              │  │    │   ├── Doc2 (ban ve) │   │
│  │ ● Classifier   │  │    │   └── Doc3 (don)    │   │
│  │ │              │  │    │                      │   │
│  │ ● Compliance   │  │    ├── Classification    │   │
│  │ │  ⚠ 1 gap    │  │    │                      │   │
│  │ ● LegalLookup  │  │    └── Gap ──→ Article  │   │
│  │ │              │  │                           │   │
│  │ ● Drafter      │  │    (graph animates live) │   │
│  │ │              │  │                           │   │
│  │ ○ Router       │  │                           │   │
│  │ ○ Summarizer   │  │                           │   │
│  │                │  │                           │   │
│  │                │  │                           │   │
│  └────────┬───────┘  └──────────────────────────┘   │
│           │                                          │
│  ┌────────▼──────────────────────────────────────┐  │
│  │ Step detail: Compliance                        │  │
│  │ Tool: case.find_missing_components             │  │
│  │ Latency: 342ms   Tokens: 1,240 → 86            │  │
│  │ Status: ✓ Success                              │  │
│  │                                                 │  │
│  │ Input: { case_id: "C-20260412-0001" }         │  │
│  │                                                 │  │
│  │ Output: [                                       │  │
│  │   {                                             │  │
│  │     name: "Văn bản thẩm duyệt PCCC",           │  │
│  │     severity: "blocker",                       │  │
│  │     citation: "NĐ 136/2020 Điều 13.2.b"       │  │
│  │   }                                             │  │
│  │ ]                                               │  │
│  │                                                 │  │
│  │ Reasoning: [expand]                             │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Interactions
- Click timeline item → expands step detail below + highlights corresponding graph node
- Click graph node → jumps to related step
- Hover edge → shows edge type
- Graph zoom + pan
- Layout: hierarchical (default) or force-directed (toggle)
- Replay: click "Replay from start" to see animation from beginning

### WebSocket events
```
{type: "agent_step_start", agent: "Compliance", case_id, timestamp}
{type: "agent_step_end", agent: "Compliance", case_id, step_id, latency, tokens}
{type: "graph_update", case_id, added_vertices: [...], added_edges: [...]}
```

### Live build choreography (t=0 → t=30s)

> This is the money shot. Every row here is a contract between backend (must emit event by this time), frontend (must render this state), and pitch team (voiceover must match). If live demo drifts from this table, rehearse again — don't rewrite the table.
>
> **Linked to:** [07-pitch/demo-video-storyboard.md Scene 3](../07-pitch/demo-video-storyboard.md) (0:40-1:05) + [artifact-inventory.md Table 3 Scene 3](./artifact-inventory.md#table-3--demo-video-timeline--artifact-first-reveal).

| t | Camera | Nodes on canvas | New edges | Active timeline | Step detail pane | Voiceover anchor |
|---|---|---|---|---|---|---|
| **0s** | `fitView` on empty canvas + dashed Case placeholder (skeleton) | 1 (Case placeholder, dashed border, opacity 0.4) | 0 | All 10 rows dimmed at opacity 0.3 | "Ready — waiting for Planner..." | Scene 3 Frame 1 starts |
| **0.5s** | hold | 2 (Case solid + Planner node just appearing) | 0 | Planner row illuminates at 50% | Planner step-start JSON preview | — |
| **1s** | hold | 2 | 1 (Planner → Case edge drawing, dashoffset 50%) | Planner row fully lit | Planner reasoning: "TTHC = Cấp phép XD, priority=normal, parallel: DocAnalyzer + SecurityOfficer + Classifier" | Scene 3 Frame 1 @ 0:41 |
| **2s** | hold | 2 + Planner glow pulse | 1 (edge complete) | Planner ✓ | Planner step-end: 892ms, 450/120 tokens, output task DAG | — |
| **4s** | hold, graph starts growing | 5 (+ DocAnalyzer, SecurityOfficer, Classifier parallel) | 4 (3 new agent→Case edges, drawing in parallel with stagger 100ms) | 3 new rows illuminate simultaneously | Multi-agent banner: "3 agents running in parallel" | Scene 3 Frame 2 @ 0:43 |
| **7s** | slight zoom out 10% via `fitView padding:0.2` to show expansion | 11 (+ 3 Document nodes from DocAnalyzer + 3 ExtractedEntity children of first doc) | 10 (Document→Bundle edges + Entity→Document edges) | DocAnalyzer ✓, others still running | Last clicked: Document "GCN QSDĐ" with 3 entities extracted | — |
| **10s** | auto-pan to parallel branches region | 16 (+ more entities, + MATCHES_TTHC Classification node) | 14 (incl. MATCHES_TTHC edge animating) | Classifier ✓, Security Officer ✓, Planner ✓ | Classifier output: "TTHC matched: 1.004415 Cấp phép XD (confidence 0.96)" | Scene 3 Frame 2 @ 0:52 |
| **14s** | hold | 17 (+ Compliance agent node appearing) | 15 | Compliance row lights up, spinning | Compliance step-start: Gremlin query building | — |
| **18s** | **auto-pan + zoom** to Compliance region (important event: `gap_found` coming) | 19 (+ Compliance ✓ + Gap node amber appearing with **pulse + shake** animation) | 17 (+ `HAS_GAP` amber edge drawing with warning color) | Compliance ✓ with ⚠ 1 gap badge | Compliance step-end: **Gremlin query visible as pre-block**, output JSON with Gap: "Văn bản thẩm duyệt PCCC", severity: blocker, citation: NĐ 136/2020 Điều 13.2.b | Scene 3 Frame 3 @ 0:58-1:03 |
| **22s** | hold, slight pan toward right edge | 20 (+ LegalLookup agent node) | 17 | LegalLookup row lights up | LegalLookup step-start: vector recall via Hologres Proxima | Scene 3 Frame 3 @ 1:02 |
| **26s** | auto-pan to LegalLookup result | 22 (+ Article node + Citation node chain, both purple) | 19 (+ Citation edge from Gap to Article, **drawing with emphasis**) | LegalLookup ✓, Compliance ✓, Classifier ✓ | LegalLookup step-end: Article "NĐ 136/2020 Điều 13 khoản 2 điểm b" retrieved, text excerpt preview | Scene 3 Frame 3 @ 1:04 |
| **30s** | `fitView` to final graph shape | **~22 nodes final:** 1 Case, 1 Applicant, 3 Docs, 6 ExtractedEntities, 1 Classification, 1 Gap, 2 Articles, 1 Citation, ~6 AgentSteps | ~20 edges | Top 5 rows ✓ (Planner, DocAnalyzer, SecurityOfficer, Classifier, Compliance, LegalLookup), remaining dimmed | "Case has 1 gap, legal reference resolved, awaiting citizen response" summary | Scene 3 ends → Scene 4 begins @ 1:05 |

### Camera behavior rules

- **Initial:** `fitView({ padding: 0.2, duration: 0 })` — no animation on first mount
- **Auto-pan triggers (emphasized events):** `gap_found` (t=18s), `permission_denied` (never in this case but pattern), `decision_made` (out of scope for 30s window)
- **Default pan/zoom:** debounced `fitView({ animation: true, duration: 400 })` on every `graph_update` event, throttled to once per 400ms so rapid-fire events don't jitter the viewport
- **User interaction overrides auto-pan:** once user clicks/drags/zooms manually, suspend auto-pan for 10s, then resume. Show a subtle "[Resume auto-pan]" chip top-right.
- **Reduced motion:** disable all camera animations, jump-cut to final positions (see [design-tokens.md §4 reduced motion](./design-tokens.md#reduced-motion--legal-requirement))

### Timeline row animation

Each of 10 agent rows has 4 states:
- **Dimmed** (opacity 0.3, gray text): not yet started
- **Running** (full opacity + spinner + `--ease-emphasized` pulse on left border strip): agent currently executing
- **Complete ✓** (success-fg tick + latency label): done successfully
- **Gap ⚠** (warning-fg badge): done but produced a blocker Gap

Row transitions fade between states in 200ms.

### Initial state (t=0) details

Crucial: the judge watching the demo never sees a blank "Loading..." screen. At t=0 the canvas shows:

```
┌──────────────────────────────────────────┐
│  Timeline                  Context Graph │
│  ○ Planner      (dimmed)                 │
│  ○ DocAnalyzer  (dimmed)                 │
│  ○ SecurityOff  (dimmed)     ┌──────┐   │
│  ○ Classifier   (dimmed)     │ Case │   │
│  ○ Compliance   (dimmed)     │(dash)│   │
│  ○ LegalLookup  (dimmed)     └──────┘   │
│  ○ Consult      (dimmed)                 │
│  ○ Summarizer   (dimmed)                 │
│  ○ Drafter      (dimmed)                 │
│  ○ Router       (dimmed)                 │
│                                           │
│  Step detail:                             │
│  "Ready — waiting for Planner..."        │
└──────────────────────────────────────────┘
```

The dashed Case placeholder acts as anchor so the viewport isn't empty. The timeline shows all 10 agents so the viewer understands "this pipeline has 10 specialized agents" before anything runs.

### Loading / skeleton

Before WebSocket connects (pre-case):

```
┌──────────────┬───────────────────────────┐
│ ▒▒▒▒▒▒▒▒    │                             │
│ ▒▒▒▒▒▒      │   [Cytoscape canvas area    │
│              │    dimmed + "Connecting    │
│ ▒▒▒▒▒▒▒▒    │    to case..." caption]    │
│ ▒▒▒▒▒▒      │                             │
│              │                             │
│ ▒▒▒▒▒▒▒▒    │                             │
│              │                             │
└──────────────┴───────────────────────────┘
```

As soon as `connected` + `subscribed` events arrive, transition to t=0 state above (400ms fade).

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| WS disconnect mid-trace | Top banner `<ConnectionLostBanner>` + reconnect countdown + **cached graph freezes** (no fake updates — "animations must not lag reality") + timeline rows show "paused" chip | Auto-reconnect with exponential backoff; once reconnected, replay missed events from server buffer |
| Agent step timeout (no `agent_step_end` within 30s) | Row turns amber with `⏳ Running long...` instead of spinner | Server-side timeout detection + surface to user |
| Agent error | Row turns red with error icon, detail pane shows error message | Retry button if agent supports it |
| Graph layout fails (>1000 nodes) | Fallback to grid layout + warning banner "Graph too large, using simple layout" | Cluster by agent type |

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §3](./artifact-inventory.md#3-agent-trace-viewer-signature):
- **MUST:** #15 AgentStep (all 10), #7 Gremlin query text, #3 ExtractedEntity nodes, #4 Classification edge, #6 Gap + edge, #8 Citation + edge, #14 Routing, #20/#21 PermissionDenied if any
- **SHOULD:** #2 Document nodes, #19 Decision node, #17 Draft node
- **MAY:** #18 Published node, #13 Opinion node

### Demo moment

For the 2:30 pitch video, the Agent Trace Viewer runs at natural speed (~30s) during Scene 3 (0:40-1:05 = 25s of video). To fit, either:
- **Option A:** cut from t=0 to t=8s, then t=18s to t=30s (compresses middle where parallel agents all finish)
- **Option B:** run at 1.25× speed during recording, re-pace voiceover
- **Recommended:** Option A — natural speed feels more authentic; the 8s→18s gap (when DocAnalyzer/Classifier finish) is the least narratively-important.

Rehearse the voiceover to land on gap reveal at precisely t=18s (= 0:58 in video).

---

## 4. Compliance Workspace — Chuyên viên

### Purpose
Anh Tuấn (Persona 3) xử lý case. Thấy checklist, legal panel, có thể 1-click consult.

### Route
- `/compliance/[case_id]`

### Layout (3-column)
```
┌──────────────────────────────────────────────────────┐
│ [nav] C-20260412-0001 — Cấp phép XD                  │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────┐ ┌────────────────┐ ┌───────────────┐  │
│  │Documents │ │ Compliance      │ │ Legal Panel   │  │
│  │          │ │ Checklist       │ │               │  │
│  │ • don_   │ │                 │ │ Căn cứ pháp lý│  │
│  │   cpxd   │ │ ✓ Đơn đề nghị   │ │               │  │
│  │ • gcn_   │ │ ✓ GCN QSDĐ      │ │ Luật XD 2014  │  │
│  │   qsdd   │ │ ✓ Bản vẽ       │ │ Điều 95       │  │
│  │ • ban_ve │ │ ✓ Cam kết MT   │ │   [click để   │  │
│  │ • ...    │ │ ⚠ VB PCCC      │ │   mở full]    │  │
│  │          │ │                 │ │               │  │
│  │ [Click   │ │ Compliance      │ │ NĐ 15/2021   │  │
│  │  to      │ │ Score: 80%      │ │ Điều 41       │  │
│  │  preview]│ │                 │ │               │  │
│  │          │ │ Cần làm:        │ │ NĐ 136/2020  │  │
│  │          │ │ [Xin ý kiến    │ │ Điều 13.2.b   │  │
│  │          │ │  Pháp chế]     │ │ [view excerpt]│  │
│  │          │ │ [Đề xuất đ.xuất│ │               │  │
│  │          │ │  công dân BS]  │ │               │  │
│  │          │ │                 │ │               │  │
│  └──────────┘ └────────────────┘ └───────────────┘  │
│                                                       │
│  ┌─────────────────────────────────────────────────┐│
│  │ [Tóm tắt | Chi tiết | Lịch sử | Audit trail ]  ││
│  │                                                   ││
│  │ [content based on tab]                            ││
│  └─────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

### Key features
- Documents column: clickable thumbnails, preview on hover
- Compliance checklist: auto-filled from Compliance agent, editable for chuyên viên
- Legal panel: clickable citations jump to [KG Explorer](#10-kg-explorer--vietnamese-legal-knowledge-graph) (new screen 10)
- Tabs at bottom: summary (3 versions), full detail, history, audit trail
- Action buttons: consult (opens slide panel below), request more from citizen, approve, deny
- **Incoming opinion notifications:** when Anh Dũng replies via [Consult Inbox](#9-consult-inbox--chuyên-viên-pháp-chế--quy-hoạch), the Legal panel surfaces a new line item with **pulse 600ms + counter animate on unread chip** per [artifact-inventory.md §13](./artifact-inventory.md)

### Consult dialog (slide panel spec)

> Triggered by clicking "[Xin ý kiến Pháp chế]" in the compliance checklist. Produces a `ConsultRequest` vertex and kicks off the [Consult Inbox](#9-consult-inbox--chuyên-viên-pháp-chế--quy-hoạch) flow on Anh Dũng's side.
>
> **Design decision:** slide-over panel from right (NOT modal). Reason: user keeps case context visible on the left, can copy-paste from documents into the consult question, and the action feels like "routing" rather than "modal interruption" — better matches the mental model of "sending a question to a colleague."

**Dimensions:** 480px wide, full viewport height, slides in from right edge.

**Motion:** Framer Motion slide 300ms (`--duration-medium-2` + `--ease-emphasized` per [design-tokens.md §4](./design-tokens.md#4-motion--material-3-duration--easing-scale)). Background dims to `oklch(0 0 0 / 0.4)` behind the panel. Clicking outside or pressing Esc dismisses.

**Layout:**

```
                                 ┌──────────────────────┐
                                 │ ← Xin ý kiến       × │
                                 │ C-20260412-0001      │
                                 ├──────────────────────┤
                                 │                       │
                                 │ Gửi tới:              │
                                 │ [Pháp chế         ▼] │
                                 │  ├ Pháp chế          │
                                 │  ├ Quy hoạch         │
                                 │  └ Đất đai           │
                                 │                       │
                                 │ Anh/chị nhận:         │
                                 │ [Anh Dũng, Pháp chế  │
                                 │  (hiện online)]       │
                                 │                       │
                                 │ Priority:             │
                                 │ (○) Normal  ( ) Urgent│
                                 │                       │
                                 │ Dự kiến trả lời:      │
                                 │ 2-4 giờ               │
                                 │ (dựa trên queue hiện) │
                                 ├──────────────────────┤
                                 │ Câu hỏi (auto-điền): │
                                 │ ┌─────────────────┐  │
                                 │ │ Công trình 500m²│  │
                                 │ │ tại KCN Mỹ Phước│  │
                                 │ │ có thuộc diện   │  │
                                 │ │ phải thẩm duyệt │  │
                                 │ │ PCCC theo NĐ    │  │
                                 │ │ 136/2020 Điều 13│  │
                                 │ │ không? Chủ hồ sơ│  │
                                 │ │ cho rằng không, │  │
                                 │ │ xin anh/chị xem │  │
                                 │ │ xét.            │  │
                                 │ │                  │  │
                                 │ │ [rich text edit] │  │
                                 │ └─────────────────┘  │
                                 ├──────────────────────┤
                                 │ Pháp lý đính kèm:    │
                                 │ (từ LegalLookup)     │
                                 │                       │
                                 │ [✓] NĐ 136/2020 Đ.13 │
                                 │ [✓] QCVN 06:2022/BXD │
                                 │ [ ] Luật PCCC 2001   │
                                 │ [+ Thêm citation]    │
                                 ├──────────────────────┤
                                 │ Tài liệu đính kèm:   │
                                 │ [✓] ban_ve.pdf       │
                                 │ [✓] cam_ket_mt.pdf   │
                                 │ [ ] gcn_qsdd.jpg     │
                                 │ (select which docs   │
                                 │  to share)           │
                                 ├──────────────────────┤
                                 │ [Hủy]  [Gửi →]      │
                                 └──────────────────────┘
```

**Pre-fill logic:**
- **Câu hỏi auto-filled** by Consult Agent summarizing the gap context (triggered immediately on panel open, takes ~2s with skeleton shimmer on textarea)
- **Pháp lý checklist pre-checked** from LegalLookup's output on the case (the same citations visible in the Legal panel)
- **Tài liệu pre-checked:** only docs relevant to the specific question (DocAnalyzer classifies relevance)
- **Recipient dropdown defaults** to the dept whose specialty matches the question domain (Consult Agent classification)

**Submission flow (per [artifact-inventory.md §12](./artifact-inventory.md)):**

| Step | UI action | Duration | Next state |
|---|---|---|---|
| 1 | Click "Gửi →" | — | Button enters loading state |
| 2 | Button → spinner + "Đang gửi..." | 600ms mock min (feels real, not instant) | — |
| 3 | WS event `consult_request` fires → server persists ConsultRequest vertex | — | — |
| 4 | Panel slides out right (300ms `--ease-accelerate`) | 300ms | Dimmed bg fades out |
| 5 | Toast success top-right: "Đã gửi ý kiến tới Anh Dũng - Pháp chế. Dự kiến trả lời: 2-4 giờ" | 4s dismiss | — |
| 6 | In Compliance WS header: new "⏳ Đang chờ ý kiến pháp chế" chip appears | fade-in 250ms | — |
| 7 | In Agent Trace Viewer (if open elsewhere): new `ConsultRequest` node appears with dashed edge from Case | fade + pulse 600ms | — |
| 8 | In Anh Dũng's Consult Inbox (if open): new list item slides in + counter-animate unread badge + notification bell pulse | slide-in 300ms | — |

**Async response surfacing (when Anh Dũng submits opinion, 3 delivery paths):**

1. **In-app notification** — bell icon in header pulses + counter animates + slide-in notification "Anh Dũng đã trả lời ý kiến cho C-20260412-0001"
2. **WS event** `opinion_received` → automatic surfacing:
   - In Compliance WS Legal panel, a new line item slides in: "💬 Pháp chế - Anh Dũng (2h trước): [opinion excerpt, click để xem]"
   - Pulse 600ms glow on the new line
   - In Agent Trace Viewer (if open), `Opinion` vertex appears in the case graph with edge from ConsultRequest
3. **Email fallback** — if user is offline/not active in-app, email sent with deep link back to Compliance WS at this exact case

**Error states:**

| Error | UI pattern | Recovery |
|---|---|---|
| Recipient offline (Anh Dũng disconnected) | Panel warns before submit "Anh Dũng đang offline. Dự kiến trả lời: 12-24h" + asks to confirm or reroute to backup | Send anyway OR pick backup (Chị Mai) |
| Duplicate consult pending | "Đã có 1 consult đang chờ trên case này. Xem trạng thái hiện tại?" | Link to existing request instead of creating duplicate |
| Submit timeout (WS fails) | Panel stays open, shows error banner + retry. Draft textarea preserved in localStorage | Retry or copy-paste elsewhere |
| Rate-limited | "Bạn đã gửi quá nhiều consult trong 10 phút. Thử lại sau 5 phút." | Wait or escalate |

### States (full screen)
- Empty (case not yet loaded): skeleton per section
- Loading (fetching case details): shimmer on documents + compliance checklist
- Consult pending (after submission): header chip + Legal panel placeholder
- Opinion received (Pháp chế responded): Legal panel highlights new line + unread dot
- Error (API fail): retry banner

---

## 5. Department Inbox — Kanban

### Purpose
Overview of all cases for a department. Quick triage.

### Route
- `/inbox`

### Layout (Kanban 5 columns)
```
┌──────────────────────────────────────────────────────┐
│ [nav] Phòng Quản lý XD — Sở XD Bình Dương           │
├──────────────────────────────────────────────────────┤
│                                                       │
│ Mới      Comp OK  Đang xử lý  Chờ consult  Quyết định│
│ (3)      (5)      (12)        (4)          (2)       │
│                                                       │
│ ┌───┐    ┌───┐    ┌───┐        ┌───┐        ┌───┐   │
│ │C1 │    │C5 │    │C9 │        │C13│        │C17│   │
│ │...│    │...│    │...│        │...│        │...│   │
│ │80%│    │100│    │95 │        │90 │        │100│   │
│ │7d │    │5d │    │⚠2d│        │4d │        │1d │   │
│ └───┘    └───┘    └───┘        └───┘        └───┘   │
│ ┌───┐    ┌───┐    ┌───┐                              │
│ │C2 │    │C6 │    │C10│                              │
│ └───┘    └───┘    └───┘                              │
│                   ┌───┐                              │
│                   │C11│                              │
│                   └───┘                              │
└──────────────────────────────────────────────────────┘
```

Each card shows: case ID, TTHC summary, compliance score, SLA countdown, classification badge.

Drag-and-drop between columns (with confirmation for status changes).

SLA countdown uses color: green → yellow → red as time runs out — via counter animate + color transition per [design-tokens.md §4 motion tokens](./design-tokens.md#4-motion--material-3-duration--easing-scale).

### Loading / skeleton

```
Mới      Comp OK  Đang xử lý  Chờ consult  Quyết định
(▒)      (▒)      (▒)         (▒)          (▒)

┌───┐    ┌───┐    ┌───┐        ┌───┐        ┌───┐
│▒▒▒│    │▒▒▒│    │▒▒▒│        │▒▒▒│        │▒▒▒│
│▒▒▒│    │▒▒▒│    │▒▒▒│        │▒▒▒│        │▒▒▒│
│▒▒ │    │▒▒ │    │▒▒ │        │▒▒ │        │▒▒ │
└───┘    └───┘    └───┘        └───┘        └───┘
```

5 placeholder cards in each column with shimmer loop. SSR renders column headers; card list streams in via CSR + `dept:{id}:inbox` WS subscription. First paint ≤200ms.

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| WS disconnect | Top banner "Cập nhật tự động đang kết nối lại..." + cards freeze (no phantom movement) | Auto-reconnect, replay missed moves |
| Drag-drop fails (API) | Card snaps back to origin column + toast "Không di chuyển được, thử lại" | User retries |
| Case load fail in column | Placeholder card with "[⚠ Không tải được]" + retry | Per-card retry |
| Concurrent edit (another staff moved same case) | Toast "Chị X vừa chuyển case này sang cột Y" + auto-refresh that case | Live sync |

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §5](./artifact-inventory.md#5-department-inbox-kanban):
- **MUST:** Case cards with #10 Compliance score, #11 SLA countdown, #5 Classification badge, #25 Status change animation, #14 Routing decision
- **SHOULD:** #6 Gap indicator on cards, #12/#13 Consult status chip
- **MAY:** #24 Anomaly alerts banner

---

## 6. Leadership Dashboard

### Purpose
Chị Hương (Persona 4) gets bird's-eye view + quick approve workflow.

### Route
- `/dashboard`

### Layout
```
┌──────────────────────────────────────────────────────┐
│ [nav] Dashboard — Sở XD Bình Dương                  │
├──────────────────────────────────────────────────────┤
│                                                       │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                │
│ │ 1,247│ │ 94%  │ │ 8    │ │ 15   │                │
│ │Active│ │SLA   │ │Over- │ │Cần   │                │
│ │cases │ │hit   │ │due   │ │ký     │                │
│ └──────┘ └──────┘ └──────┘ └──────┘                │
│                                                       │
│ ┌─────────────────────┐ ┌───────────────────────┐   │
│ │ SLA Status by TTHC  │ │ Processing Time Trend  │   │
│ │                      │ │                         │   │
│ │ CPXD  ████████ 89%  │ │ [line chart 30 days]   │   │
│ │ GCN   ██████   72%  │ │                         │   │
│ │ ĐKKD  █████████ 98% │ │                         │   │
│ │ LLTP  ██████   75%  │ │                         │   │
│ └─────────────────────┘ └───────────────────────┘   │
│                                                       │
│ Cần phê duyệt (15):                                  │
│ ┌──────────────────────────────────────────────┐    │
│ │ C-20260412-0001  CPXD  Compliance 94%  [dup]│    │
│ │ C-20260412-0002  CPXD  Compliance 100% [dup]│    │
│ │ ...                                           │    │
│ │ [Xem tất cả]  [Ký loạt chọn]                 │    │
│ └──────────────────────────────────────────────┘    │
│                                                       │
│ [Xuất báo cáo NĐ 61] [AI Weekly Brief ⚡]            │
└──────────────────────────────────────────────────────┘
```

### Key features
- 4 headline metrics at top
- 2 charts: SLA status by TTHC + processing time trend (Recharts or Tremor blocks — see [design-system.md Implementation references](./design-system.md))
- Approve queue at bottom (quick-click to review)
- Export NĐ 61 compliance report (1-click)
- "AI Weekly Brief" button uses Hologres AI Functions to call Qwen for weekly summary — live demo of inside-SQL LLM

### Loading / skeleton

```
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ ▒▒▒▒ │ │ ▒▒▒▒ │ │ ▒▒▒▒ │ │ ▒▒▒▒ │
│ ▒▒   │ │ ▒▒   │ │ ▒▒   │ │ ▒▒   │
└──────┘ └──────┘ └──────┘ └──────┘

┌─────────────────────┐ ┌───────────────────────┐
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │
│ ▒▒▒▒▒▒▒▒▒▒▒▒       │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒       │
│ ▒▒▒▒▒▒▒▒           │ │ ▒▒▒▒▒▒▒▒▒▒           │
│ ▒▒▒▒▒▒▒▒▒▒▒▒       │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒     │
└─────────────────────┘ └───────────────────────┘

┌──────────────────────────────────────────────┐
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒    │
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒    │
└──────────────────────────────────────────────┘
```

Metrics start at 0 → counter-animate 400ms when data arrives. Charts render skeleton bars first (same shape, gray fill), then morph to real data with 400ms transition. Approve queue streams row-by-row with 50ms stagger.

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| Metrics API fail | Each metric card shows "—" + `<RetryButton>` below | Per-card retry |
| Chart render fail | Chart area shows "Không tải được biểu đồ [thử lại]" + cached screenshot fallback if available | Retry |
| Export NĐ 61 fails | Toast "Xuất báo cáo thất bại. [Thử lại] hoặc xem log" | Retry |
| AI Weekly Brief fails (Hologres connection) | Modal shows error + fallback to cached brief from last week | Retry or use cached |
| Batch approve fails partially (5 of 10 approved, 5 failed) | Results modal showing success/failure per case + retry for failures | Per-case retry |

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §6](./artifact-inventory.md#6-leadership-dashboard):
- **MUST:** #10 Compliance score (KPI + queue), #11 SLA countdown (metric + chart), #16 Summary card, #17 Draft preview, #18 Published status, #19 Decision buttons
- **SHOULD:** #30 AI Weekly Brief, #24 Anomaly warning
- **MAY:** #8 Citation quick view

### Scene 5 choreography — Processing continues → Leadership approve (1:20 → 1:45)

> Scene 5 spans multiple screens: Citizen Portal (resume upload), Intake mini, Department Inbox (Kanban card movement), Compliance Workspace brief glance, then Leadership Dashboard approve flow. The "money shot" is on Leadership Dashboard — the table below covers that primary surface with cross-refs to other screens for non-primary beats.

| t | Primary screen | UI event | Animation | Voiceover anchor |
|---|---|---|---|---|
| **0s (=1:20)** | Citizen Portal (cut from Scene 4) | "8 days later" time-skip title card overlay | full-screen fade 400ms with title text typewriter 800ms | "8 ngày sau..." |
| **2s (=1:22)** | Citizen Portal tracking | Anh Minh re-uploads PCCC document | quick 2s montage (file upload + ✓) | "anh Minh upload PCCC..." |
| **4s (=1:24)** | Department Inbox (cut to Tuấn's screen, brief) | `case_status_change` event → card slides from "Chờ bổ sung" column to "Đang xử lý" column | Kanban card slide 300ms `--ease-emphasized` + subtle glow on arrival | "Router chuyển hồ sơ..." |
| **6s (=1:26)** | Agent Trace mini view (brief cut, maybe picture-in-picture top-right) | Consult agent fires: ConsultRequest → Opinion ping-pong visible as 2 new nodes | fade + glow pulse 600ms each | "Consult Agent auto xin ý kiến..." |
| **9s (=1:29)** | Agent Trace mini | Opinion vertex appears with glow pulse | pulse 600ms | — |
| **12s (=1:32)** | **Leadership Dashboard** (cut to Hương's screen, primary) | Dashboard opens: 4 KPIs counter-animate from 0 to real values (1247 cases, 94% SLA, 8 overdue, 15 cần ký) | counter animate 800ms `--ease-emphasized` stagger 100ms per card | "Chị Hương mở Leadership Dashboard..." |
| **14s (=1:34)** | Leadership Dashboard | Charts render (SLA by TTHC + processing time trend) | skeleton → real data morph 400ms | — |
| **16s (=1:36)** | Leadership Dashboard | "Cần phê duyệt (15)" section scrolls into view | scroll 400ms | — |
| **17s (=1:37)** | Leadership Dashboard | Hương clicks C-20260412-0001 row → expand inline OR side drawer slides in (choice: inline for Scene 5 speed) | inline expand 300ms | "...thấy tóm tắt executive 3 dòng..." |
| **19s (=1:39)** | Leadership Dashboard expanded | Executive summary populates (3 lines of Summarizer output): "Cấp phép XD cho N*** Văn M***. Nhà xưởng 500m² tại KCN Mỹ Phước. Compliance 100%." + badges "Pháp chế ✓ Quy hoạch ✓" | fade + stagger 50ms | — |
| **21s (=1:41)** | Leadership Dashboard expanded | Compliance bar animates 0→100% green + 2 green dept badges pulse | counter 400ms + pulse 600ms | "...compliance 100%..." |
| **23s (=1:43)** | Leadership Dashboard expanded | Big green "Phê duyệt" button at right of expanded row pulses subtly to invite click | subtle pulse 2s loop | "...1 click..." |
| **25s (=1:45)** | Leadership Dashboard | Hương clicks "Phê duyệt" → button loading 400ms → success toast + status badge transitions to "Đã duyệt, đang sinh văn bản" | button glow pulse 600ms + state transition 400ms | "phê duyệt chỉ 1 click" |

### Scene 5 camera / cut rules

- **Fast cuts** (2-3s per cut) for the 8-day montage portion (t=0→11s)
- **Settle** on Leadership Dashboard for t=12→25s (the 14-second primary beat)
- **Picture-in-picture** Agent Trace mini at t=6→11s: top-right corner 320×200, shows Consult ping-pong nodes appearing without cutting away from the main scene
- **No camera pan** on Leadership Dashboard itself — it's a dashboard, viewport stays fixed, content updates in place

### Cross-screen WS events driving Scene 5

Per [realtime-interactions.md Demo moment mapping](./realtime-interactions.md#demo-moment-mapping):

- t=4s → `case_status_change` on `case:C-001` topic
- t=4s → `graph_update` with `ASSIGNED_TO` edge on `case:C-001`
- t=6s → `consult_request` event on `case:C-001` (pings Anh Dũng's Consult Inbox if open in another window)
- t=9s → `opinion_received` event (auto-acknowledged in demo seed data)
- t=17s → client fetch + cached summary render (Hương clicking the row)
- t=25s → `decision_made` event on `case:C-001`

### Batch approve variant (for live demo Q&A, not main video)

When judges ask "can she approve multiple at once?", the presenter can demo this in Q&A:

| t | UI event | Animation |
|---|---|---|
| 0s | Click "Ký loạt chọn" button | button loading 600ms |
| 0.6s | Modal confirms: "Ký 10 văn bản? Tổng thời gian tiết kiệm: 50 phút" | slide-up 300ms |
| 2s | Confirm + digital signature prompt (PKI mock) | modal replaces content |
| 4s | Progress bar shows 10 documents signing one by one | stagger 400ms per doc |
| 8s | All 10 ✓ | final pulse + "10 giấy phép đã phát hành" toast |
| 10s | Dashboard refreshes, queue drops by 10 | counter animate 800ms |

---

## 7. Security Console — CIO / IT Security

### Purpose
Anh Quốc (Persona 6) monitors security, reviews audit trails, manages access.

### Route
- `/security`

### Layout (dense, log-style)
```
┌──────────────────────────────────────────────────────┐
│ [nav] Security Console      [Run demo: A|B|C]       │
├──────────────────────────────────────────────────────┤
│                                                       │
│ Tabs: [Audit Log] [Denied Access] [Agent Status]     │
│       [Policies] [Users]                             │
│                                                       │
│ Audit Log — Live                                     │
│ ┌──────────────────────────────────────────────────┐│
│ │ 14:32:15  user:chi_huong    view  Case C-...-01  ││
│ │           → allow  (Confidential)                 ││
│ │ 14:32:10  agent:Compliance  write Gap            ││
│ │           → allow                                 ││
│ │ 14:31:45  user:other        view  Case C-...-07  ││
│ │           → DENY  (clearance insufficient) 🔴    ││
│ │ 14:31:30  agent:LegalLookup query Article         ││
│ │           → allow                                 ││
│ │ ...                                                ││
│ └──────────────────────────────────────────────────┘│
│                                                       │
│ Filter: [Actor ▼] [Action ▼] [Result ▼] [Time ▼]   │
│                                                       │
│ Stats (today):                                       │
│ 12,345 events  |  45 denied  |  3 anomalies detected │
│                                                       │
│ Anomaly: user 'xyz' had 12 denied access in 10m      │
│ [Review] [Disable user]                              │
└──────────────────────────────────────────────────────┘
```

### Features
- Live audit log stream (WebSocket via `security:audit` topic)
- Filters by actor, action, result, time range
- Anomaly detection alerts at bottom
- Forensic replay: click a case ID to see full reasoning trace + audit trail
- Policy editor (admin): add/edit agent profiles as YAML + preview
- User management: clearance + department assignment
- **Agent Status tab** — mission-control view of all 10 agents (see subsection below)

### Agent Status tab

> Answers the judge Q&A question "which agents are running right now?" without needing to navigate away. Also serves as a health dashboard for ops.

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│ Agents — Live                        Last update: 14:32:15│
├──────────────────────────────────────────────────────────┤
│                                                            │
│ ┌────────────────┬─────────────┬──────────┬──────────┐   │
│ │ Agent          │ Running/Idle│ Avg lat. │ p95 lat. │   │
│ ├────────────────┼─────────────┼──────────┼──────────┤   │
│ │ ● Planner      │ idle        │ 892ms    │ 1240ms   │   │
│ │ ● DocAnalyzer  │ 3 running   │ 2.1s     │ 4.8s     │   │
│ │ ● Classifier   │ 1 running   │ 145ms    │ 280ms    │   │
│ │ ● Compliance   │ 2 running   │ 342ms    │ 680ms    │   │
│ │ ● LegalLookup  │ idle        │ 420ms    │ 890ms    │   │
│ │ ● Router       │ idle        │ 38ms     │ 75ms     │   │
│ │ ● Consult      │ 1 running   │ 1.2s     │ 2.8s     │   │
│ │ ● Summarizer   │ idle        │ 1.8s     │ 3.2s     │   │
│ │ ● Drafter      │ idle        │ 4.5s     │ 8.1s     │   │
│ │ ● SecurityOff  │ 2 running   │ 125ms    │ 240ms    │   │
│ └────────────────┴─────────────┴──────────┴──────────┘   │
│                                                            │
│ 24h stats:                                                 │
│ 12,450 agent steps  |  98.7% success  |  1 timeout        │
│                                                            │
│ Per-agent detail: click any row →                          │
│   - Recent 20 steps (timestamp, case_id, latency, tokens) │
│   - Token usage 24h (in/out totals + cost estimate)       │
│   - Error rate chart (line chart, last 24h)               │
│   - Current task queue depth                               │
└──────────────────────────────────────────────────────────┘
```

**Status indicator colors (left dot):**
- Green `--gov-success-9`: agent healthy, p95 within SLO
- Amber `--gov-warning-9`: degraded (p95 > 2× target OR error rate > 5%)
- Red `--gov-danger-9`: circuit breaker tripped OR last 5 calls failed

**Realtime updates via `agent:status` WS topic:**
- Counter animates when "running" count changes (`--duration-medium-4`)
- Latency numbers update every 5s (throttled) with subtle fade transition on change
- No animations when agent is idle — avoid noise

**Click a row → slide panel from right:**

```
                              ┌──────────────────────┐
                              │ ← Planner            ×│
                              │ Status: idle          │
                              ├──────────────────────┤
                              │ 24h stats             │
                              │ • Steps: 1,247        │
                              │ • Success: 99.8%      │
                              │ • Avg latency: 892ms  │
                              │ • Tokens: 145k / 38k  │
                              │ • Cost: ~$0.42        │
                              ├──────────────────────┤
                              │ Error rate (24h)      │
                              │ [line chart]          │
                              ├──────────────────────┤
                              │ Recent steps (20)     │
                              │ 14:32:15 C-001 892ms  │
                              │ 14:31:48 C-002 920ms  │
                              │ 14:31:02 C-003 745ms  │
                              │ ...                    │
                              ├──────────────────────┤
                              │ [View in Agent Trace]│
                              └──────────────────────┘
```

**Demo hook:** During pitch Q&A, if a judge asks "how many agents are there?" or "what's the orchestration look like?" — click to Agent Status tab, show all 10 agents live with latency numbers. Takes 3 seconds, gives a concrete answer.

**Artifacts surfaced (add to inventory):**
- Agent running count + latency (derived from `agent_step_start`/`_end` events, client-side aggregated)
- 24h stats (server-provided from Hologres analytics)

### Scene 7 tight timing (Security Console 2:00 → 2:15)

> The permission demo harness (above) spells out what happens per scene. This table adds precise timing for the rapid 15-second sequence.

| t | Scene | Action | Animation | Voiceover |
|---|---|---|---|---|
| **0s (=2:00)** | Intro | Cut to Security Console Audit Log tab, Classification banner at top transitions to CONFIDENTIAL blue as hero case classified | banner fade 200ms | "SecurityOfficer tự động flag Confidential..." |
| **2s (=2:02)** | Setup | Presenter hovers to top-right "[Run demo: A]" button | hover state | "Permission engine 3 tầng bảo vệ..." |
| **3s (=2:03)** | **Scene A start** | Click A | button loading 400ms | "Tier 1 SDK Guard reject..." |
| **3.5s** | Scene A | Audit row slides in from top, flashes red, shakes | stagger + flash 400ms + shake 200ms | — |
| **4s** | Scene A | Toast slides in from right bottom: "❌ Denied at Tier 1" + reason | slide 300ms | — |
| **6s (=2:06)** | **Scene B start** | Click B | button loading 400ms | "Tier 2 GDB native RBAC reject..." |
| **6.5s** | Scene B | Same pattern as A but different reason string | shake + flash | — |
| **8s** | Scene B | Toast B | — | — |
| **9s (=2:09)** | **Scene C start** | Click C | button loading 400ms | "Tier 3 Property Mask redact PII..." |
| **9.5s** | Scene C | Document Viewer slides in from right (sheet), Classification banner UNCLASSIFIED green visible, fields show solid-bar redaction | slide 300ms | — |
| **11s (=2:11)** | Scene C pause | Hold for 1.5s showing redacted state clearly | — | "...khi user cấp clearance cao hơn..." |
| **12s (=2:12)** | Scene C elevation | Click [Nâng clearance] → ElevationModal slides up, PIN entered, confirmed | modal 300ms + 500ms mock auth | — |
| **13s (=2:13)** | Scene C reveal | Classification banner transitions UNCLASSIFIED green → CONFIDENTIAL blue (400ms), solid bars unmount, revealed content crossfades in (opacity 0→1, 250ms) | sequence 650ms | "...mask gradually reveal..." |
| **14s (=2:14)** | Scene C further elevation (optional) | Quick click to Secret level, location reveals "3km from military base" | same sequence 650ms | — |
| **15s (=2:15)** | End Scene 7 | Presenter transitions out | — | Scene 8 begins |

**Crucial rehearsal note:** Scene 7 is the densest 15 seconds in the entire demo (3 scenes in 15s = 5s per scene on average, minus transitions). Rehearse until button timing is muscle memory. If live demo drifts, fall back to pre-recorded video of just Scene 7.

### Permission demo harness

> Critical for Scene 7 (2:00-2:15) of the demo video. All three permission-denied scenarios are triggered from a single button group at the top-right of Security Console. Each button fires a scripted scenario via `POST /demo/scene/:id` which creates the exact conditions on the server, then the UI reaction follows naturally from real WS events (not faked animations).

**Trigger UI (top-right of Security Console header):**

```
┌─────────────────────────────────────────┐
│ Security Console      [Run demo: A|B|C] │
│                       D+A  D+B  D+C     │
└─────────────────────────────────────────┘
```

- 3-button outline group, keyboard shortcuts `D+A`, `D+B`, `D+C` (hold D then letter)
- All three discoverable via `⌘K` palette search "Run demo scene"
- Each button disabled for 3s after click to prevent accidental double-trigger mid-demo
- Tooltips show exactly what will happen ("A: Summarizer attempts to read national_id → denied at SDK Guard")

**Scene A — SDK Guard reject (Tier 1):**

1. Click `[Run demo: A]` OR press `D+A`
2. Backend: Summarizer agent invoked with task "summarize Applicant for case X" → tries to read `Applicant.national_id` → SDK Guard checks agent profile → denies
3. WS event `permission_denied` with `tier: "sdk_guard"`, reason: "Property 'national_id' not in read scope for agent 'Summarizer'"
4. UI reaction (per [artifact-inventory.md #20](./artifact-inventory.md)):
   - Audit log row slides in from top + flashes red background 400ms + shake animation 200ms
   - Toast slides from right: `<PermissionDeniedToast>` with Tier 1 badge + reason string + audit_id link
   - Sound (if enabled): subtle negative "deny" chime
5. Button re-enables after 3s

**Scene B — GDB RBAC violation (Tier 2):**

1. Click `[Run demo: B]` OR press `D+B`
2. Backend: LegalLookup agent (which has READ privileges on `Article` but NOT WRITE on `Gap`) tries to write a Gap vertex → GDB native RBAC rejects at storage layer
3. WS event `permission_denied` with `tier: "gdb_rbac"`, reason: "agent_legallookup lacks WRITE privilege on label Gap"
4. UI reaction:
   - Same audit log row pattern as Scene A but with different reason string
   - Toast with Tier 2 badge
   - If Agent Trace Viewer is visible in another window (e.g. side-by-side demo layout): failed edge write attempt visualized as a ghost edge that fades in then out with red color

**Scene C — Property mask elevation (Tier 3):**

1. Click `[Run demo: C]` OR press `D+C`
2. Backend: opens a case with Confidential classification, user clearance = Unclassified → SDK Guard applies property mask → Document Viewer opens in right-side slide panel
3. UI reaction (per [artifact-inventory.md #22](./artifact-inventory.md)):
   - Right-side Document Viewer slides in (300ms `--ease-emphasized`)
   - Fields show **solid bar redaction** (NOT blur — per [design-system.md classification section](./design-system.md)): `national_id: ▓▓▓▓▓▓▓▓`, `location: ▓▓▓▓▓▓▓▓`
   - 2-second pause for visual impact
   - User clicks "[Nâng clearance lên Confidential]" button → step-up auth modal (per [design-system.md Classification banner section](./design-system.md)) → accepts
   - Solid bars **crossfade** to revealed content (opacity 0→1 on revealed text, 250ms, NOT blur unblur): `national_id: 079****1234`, `location: Lô X, KCN Mỹ Phước`
   - Sticky classification banner at top of viewer changes from "UNCLASSIFIED" green to "CONFIDENTIAL" blue
   - Further elevation to Secret → location reveals additional detail "3km from military base"
   - Audit log shows both elevation grants with timestamps

**Why solid bar, not blur:** research shows blur is cryptographically recoverable (deconvolution attacks) — for a government product, this is the correct security posture. Blur also reads as "consumer soft-focus" which breaks the serious tone. See [design-system.md Classification section](./design-system.md) for full rationale.

**Demo day checklist** (before stage):
- [ ] All 3 scenarios tested end-to-end the night before
- [ ] Button tooltips not blocked by any overlay
- [ ] Keyboard shortcuts work even if mouse focus is lost
- [ ] Server-side demo state resets automatically after 10 minutes (so repeated rehearsals work)
- [ ] Side-by-side window layout pre-arranged for Scene B (Agent Trace Viewer visible)
- [ ] Classification banner visible above viewport fold at 1920×1080

### Loading / skeleton

```
Tabs: [▒▒▒▒▒▒▒▒] [▒▒▒▒▒▒▒▒] [▒▒▒▒▒▒] [▒▒▒▒▒]

Audit Log — Live
┌──────────────────────────────────────────────────┐
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │
└──────────────────────────────────────────────────┘

Stats (today): ▒▒▒▒  |  ▒▒▒  |  ▒▒
```

Audit log primes with last 50 cached entries from SSR, then new rows stream in from the top via WS `security:audit` subscription with stagger 50ms.

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| WS disconnect | Critical banner (red, not yellow) "Audit stream disconnected — [reconnect]" — security is a must-not-miss context | Manual reconnect button + auto-retry |
| Demo scene fails (server 5xx) | Button revert + toast "Scenario failed to start. Check server logs." | Retry or skip to next scene |
| Anomaly service fails | Anomaly panel shows "Detection temporarily unavailable" | Non-blocking |
| Forensic replay fails | Error panel "Không tải được replay cho case X. [Báo cáo lỗi]" | Retry or escalate |

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §7](./artifact-inventory.md#7-security-console):
- **MUST:** #23 AuditEvent, #20 PermissionDenied Tier 1, #21 PermissionDenied Tier 2, #22 Classification mask, #24 Anomaly, #5 Classification filter
- **SHOULD:** #15 Agent Trace replay link
- **MAY:** User management (static)

---

## 8. Document Viewer

### Purpose
Deep view of a single case with document viewer + summaries + legal refs + audit.

### Route
- `/cases/[id]`

### Layout
```
┌──────────────────────────────────────────────────────┐
│ [nav] ← Back to inbox  C-20260412-0001              │
│                                    [approve] [deny]  │
├──────────────────────────────────────────────────────┤
│                                                       │
│ ┌────────────────────┐ ┌─────────────────────────┐  │
│ │                     │ │ Info panel               │  │
│ │                     │ │                          │  │
│ │   [PDF viewer]      │ │ TTHC: Cấp phép XD        │  │
│ │                     │ │ Applicant: N*** Văn A    │  │
│ │   With entity        │ │ Classification: ⚠Confidential│
│ │   highlights        │ │ SLA: 7 ngày còn lại      │  │
│ │   (clickable)       │ │ Compliance: 94%           │  │
│ │                     │ │                          │  │
│ │                     │ │ Tabs:                    │  │
│ │                     │ │ [Summary] [Legal] [Audit]│  │
│ │                     │ │                          │  │
│ │                     │ │ Summary (executive):     │  │
│ │                     │ │ ...                       │  │
│ │                     │ │                          │  │
│ └────────────────────┘ └─────────────────────────┘  │
│                                                       │
│ Related cases (precedent):                            │
│ [mini cards x 3]                                      │
└──────────────────────────────────────────────────────┘
```

### Features
- PDF viewer with highlighted entities (ExtractedEntity vertices)
- Click entity → popup with detail
- 3 summary tabs (executive / staff / citizen)
- Legal refs tab with clickable Citations (jump to [KG Explorer](#10-kg-explorer--vietnamese-legal-knowledge-graph))
- Audit tab with filtered audit log for this case
- Related cases (precedent search via semantic similarity)
- Approve / Deny buttons for authorized users
- **State variants:** `draft` (yellow DRAFT ribbon overlay), `pending-approval` (normal), `approved`, `published` (green seal + QR), `denied`
- **Classification banner** sticky top + bottom per [design-system.md Classification section](./design-system.md) — mandatory for any case above Unclassified

### Loading / skeleton

```
┌────────────────────┐ ┌─────────────────────────┐
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒           │
│ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │ │ ▒▒▒▒▒▒▒▒▒▒               │
│                     │ │                          │
│   [PDF skeleton     │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒           │
│    — 3 page outlines│ │ ▒▒▒▒▒▒▒▒▒▒               │
│    with shimmer]    │ │                          │
│                     │ │ Tabs:                    │
│   page 1 ▒▒▒▒▒▒▒  │ │ [▒▒] [▒▒] [▒▒]          │
│   page 2 ▒▒▒▒▒▒▒  │ │                          │
│   page 3 ▒▒▒▒▒▒▒  │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  │
│                     │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  │
│                     │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒           │
└────────────────────┘ └─────────────────────────┘
```

PDF viewer uses `react-pdf` lazy-load pattern — first page renders as soon as downloadable, remaining pages stream in. Entity highlights overlay after full download.

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| **PDF load failure** | Placeholder "Không tải được tài liệu gốc. [Thử lại] hoặc [Tải xuống trực tiếp]" + still show info panel + summaries (data survives) | Retry or direct download |
| PDF render (first page) times out | "Đang tải nặng... " spinner + "Xem dưới dạng văn bản" fallback button shows extracted text only | Text fallback |
| Entity highlight fetch fails | PDF renders without highlights, small banner "Entity markup không khả dụng" | Non-blocking |
| Summary fetch fails | Tab shows "Không tạo được tóm tắt. [Tạo lại]" | Retry Summarizer |
| Audit tab fail | Audit tab shows "Không tải được audit trail. [Thử lại]" | Retry |
| Approve/Deny fails | Button revert + toast "Lưu quyết định thất bại. [Thử lại]" | Retry |
| Permission denied mid-view (auth expired) | Modal "Phiên làm việc hết hạn. [Đăng nhập lại]" — preserves case ID for return | Re-auth + return |
| Classification mismatch (user clearance insufficient when loading) | Full-page block: "Yêu cầu clearance cao hơn để xem hồ sơ này. [Xin cấp quyền]" | Request elevation modal |

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §8](./artifact-inventory.md#8-document-viewer):
- **MUST:** #3 ExtractedEntity highlights, #2 Document label sidebar, #5 Classification banner sticky, #10 Compliance score, #16 Summary tabs (3 variants), #8 Citation legal tab, #23 AuditEvent audit tab, #11 SLA countdown, #19 Decision buttons, #17 Draft ribbon, #18 Published seal + QR
- **SHOULD:** #28 Precedent cases, #22 Classification mask (for PII), #13 Opinion history
- **MAY:** #9 Article text excerpt popover

### Draft state variant

When `case.status = 'draft_generated'`, Document Viewer renders in **draft mode**:

```
┌─────────────────────────────────────────┐
│ ░░░░░░░░░░ DRAFT ░░░░░░░░░░░░░░░░░░░░  │ ← yellow diagonal ribbon overlay
│ ░░                              (top-right)
│   [PDF preview — NĐ 30/2020 format]    │
│                                          │
│   CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM    │
│   Độc lập - Tự do - Hạnh phúc            │
│   ─────────────────                      │
│                                          │
│   Số: [auto]  /QĐ-SXD      BĐ, [date]   │
│                                          │
│   QUYẾT ĐỊNH                            │
│   V/v cấp phép xây dựng...               │
│                                          │
│   Căn cứ:                                │
│   - Luật XD 2014 Điều 95 [link]         │
│   - NĐ 15/2021 Điều 41  [link]          │
│   - Đơn đề nghị của...                   │
│                                          │
│   ...                                    │
│                                          │
│   [chữ ký số placeholder — box with     │
│    diagonal slash pattern]               │
└─────────────────────────────────────────┘

Action bar bottom: [Chỉnh sửa] [Từ chối] [Ký số + Phát hành →]
```

**DRAFT ribbon spec:**
- Diagonal ribbon in top-right corner of PDF preview area (rotate 45deg)
- Color: `--color-status-warning-solid` (amber)
- Text: "DRAFT" in uppercase, white, tracking `--tracking-widest`
- Position: absolute, top: 0, right: 0, translate(30%, 20%)
- Subtle fade-in 250ms on mount (NO pulse — it's not trying to be attention-grabbing, it's a state label)
- Never obscures legal content, but always visible

**Citations in draft** are clickable (underlined link style) even though the document isn't published yet. Click → opens KG Explorer in new tab at the cited article.

**Signature placeholder** renders as a box with diagonal hatching (SVG pattern) + text "[Chưa ký — ký số để phát hành]".

### Published state variant

When `case.status = 'published'`, Document Viewer renders in **published mode**:

- DRAFT ribbon replaced with **green seal** in same top-right position
- Seal = circular badge with GovFlow logo + "ĐÃ PHÁT HÀNH" text
- Signature placeholder replaced with actual signature block (name + title + timestamp + public key hash)
- **QR verification code** appears at bottom-right of PDF (250×250px, quiet zone, scannable at printer resolution)
- Document becomes read-only (edit button removed)
- Footer shows "Phát hành lúc: 2026-04-12 15:47" + "Hash: abc123..."

### Scene 6 choreography — Drafter + Publish (1:45 → 2:00)

> Document Viewer is the primary screen for Scene 6. This 15-second sequence shows Drafter generating the PDF → Chị Hương reviewing and signing → anh Minh receiving the result. The transition from draft → signed → published must feel tactile and weighty (this is a legal document).

| t | Screen | UI event | Animation | Voiceover anchor |
|---|---|---|---|---|
| **0s (=1:45)** | Leadership Dashboard (cut from Scene 5) → Document Viewer opens with draft state | Document Viewer mounts, PDF skeleton shimmer 500ms | fade 400ms | "Drafter Agent sinh Giấy phép XD..." |
| **1s (=1:46)** | Document Viewer (draft state) | First page of PDF renders with entity highlights, DRAFT ribbon fades in top-right | fade 250ms | — |
| **2s (=1:47)** | Document Viewer (draft) | Info panel right side populates: TTHC, Applicant, Classification, SLA, Compliance 100% | stagger 50ms per field | — |
| **3s (=1:48)** | Document Viewer (draft) | Camera scrolls/zooms to show the "Căn cứ" section — citations NĐ 15/2021 Điều 41 highlighted as clickable links | smooth scroll 400ms | "...theo đúng thể thức NĐ 30/2020 — quốc hiệu, số hiệu, trích yếu, căn cứ..." |
| **5s (=1:50)** | Document Viewer (draft) | Chị Hương's cursor hovers over NĐ 15/2021 link → tooltip appears with 2-line excerpt | tooltip fade 200ms | "...citations clickable về từng điều luật gốc..." |
| **7s (=1:52)** | Document Viewer (draft) | Cursor moves to "[Ký số + Phát hành →]" button at bottom | cursor move hold | "Chị Hương review..." |
| **8s (=1:53)** | Document Viewer (draft) → Ký modal | Click → `<SignModal>` slides up (300ms `--ease-emphasized`) with PKI signature prompt: "Nhập PIN thiết bị ký số" | slide-up 300ms + backdrop dim | "...ký số..." |
| **9s (=1:54)** | Ký modal | PIN entered, "Đang ký..." spinner 500ms | spinner | — |
| **10s (=1:55)** | Document Viewer transitioning | Modal closes, state transition begins: DRAFT ribbon **fade out 200ms** → signature block **fade in 300ms** → green seal **stamp animation 400ms** `--ease-decelerate` (scale from 1.3 → 1.0 + rotate 3deg) → classification banner remains | sequence: 200ms + 100ms gap + 300ms + 100ms gap + 400ms = 1100ms total | — |
| **11s (=1:56)** | Document Viewer (published) | QR code fades in bottom-right of PDF (opacity 0→1, 300ms) | fade 300ms | "...publish" |
| **12s (=1:57)** | Cut to anh Minh's phone (mobile view) | Phone in lock state, push notification slides from top: "GovFlow: Giấy phép của bạn đã sẵn sàng" | push anim 300ms + haptic | "Anh Minh nhận thông báo..." |
| **13s (=1:58)** | Phone (Citizen Portal tracking) | Anh Minh taps, tracking page opens, timeline updates to ✓ with green "Đã phát hành" badge + PDF preview card slides in from bottom | slide-up 400ms | "...download giấy phép..." |
| **14s (=1:59)** | Phone | [Download] button prominent, QR verification code visible in preview | static hold | "...có mã QR xác thực..." |
| **15s (=2:00)** | End Scene 6 | Anh Minh smiles thumbs up | — | "10 ngày, 1 chuyến đi" |

### Scene 6 motion tokens

| Animation | Duration | Easing | Token |
|---|---|---|---|
| DRAFT ribbon fade out | 200ms | `--ease-accelerate` | `--duration-short-4` |
| Signature block fade in | 300ms | `--ease-emphasized` | `--duration-medium-2` |
| **Seal stamp** (scale 1.3→1.0 + rotate 3deg) | 400ms | `--ease-decelerate` | `--duration-medium-4` |
| QR code fade in | 300ms | `--ease-emphasized` | `--duration-medium-2` |
| Mobile slide-up | 400ms | `--ease-emphasized` | `--duration-medium-4` |

**Seal stamp animation detail:**

```tsx
<motion.div
  initial={{ scale: 1.3, rotate: 10, opacity: 0 }}
  animate={{ scale: 1, rotate: 3, opacity: 1 }}
  transition={{
    duration: 0.4,
    ease: [0, 0, 0, 1], // --ease-decelerate
  }}
>
  <SealSvg />
</motion.div>
```

The `--ease-decelerate` is the RIGHT choice here — it gives the impression of a physical stamp being pressed down (fast motion slowing at contact). DO NOT use spring with bounce — that would feel rubbery. DO NOT use linear — that would feel mechanical. `--ease-decelerate` is the only right answer for a stamp.

The slight rotation (3deg, not 0) makes it feel hand-applied instead of digital — a tiny detail that elevates the polish. Like Dropbox's checkmark.

### Error states for draft / publish flow

| Error | UI pattern | Recovery |
|---|---|---|
| Draft generation fails (Drafter agent error) | Toast "Không sinh được bản nháp. [Sinh lại]" | Retry Drafter |
| PKI signature timeout | Modal shows "Thiết bị ký không phản hồi. Kiểm tra cable USB" | Retry or manual signature |
| Publish API fails | State reverts to draft, toast + retry button | Auto-retry 1x then manual |
| QR generation fails | Publish succeeds but QR shows "—" placeholder + async retry | QR appears later when generated |

---

## 9. Consult Inbox — Chuyên viên Pháp chế / Quy hoạch

### Purpose

Anh Dũng (Persona 5, Chuyên viên Pháp chế) mỗi sáng mở Consult Inbox để trả lời 3–5 consult requests được Consult Agent pre-analyzed. Không có screen này, Persona 5 journey broken và Consult artifacts (`ConsultRequest`, `Opinion` vertices) không có UI home — xem [artifact-inventory.md §12-13, §27-28](./artifact-inventory.md).

### Routes
- `/consult` — list of all pending + replied requests
- `/consult/[request_id]` — detail view với reply composer

### Layout (2-column, master-detail)

```
┌──────────────────────────────────────────────────────┐
│ [nav] Consult Inbox — Pháp chế (Anh Dũng)           │
│                                  [🔔 3 mới] [⚙]     │
├──────────────────────────────────────────────────────┤
│                                                       │
│ ┌──────────────┐  ┌────────────────────────────────┐│
│ │ 3 pending    │  │ C-20260412-0001 — CPXD 500m²  ││
│ │              │  │ Nguyễn Văn M*** • KCN Mỹ Phước ││
│ │ [🔴 Urgent]  │  │ [Confidential] SLA: 2 ngày     ││
│ │ C-...-0001  │  │                                  ││
│ │ CPXD PCCC    │  │ ┌─ Pre-analyzed context ─────┐ ││
│ │ SLA: 2d ⚠   │  │ │ (auto by Consult Agent)      │ ││
│ │              │  │ │                               │ ││
│ │ [▸ Normal]   │  │ │ Tóm tắt: Công trình 500m²    │ ││
│ │ C-...-0002  │  │ │ tại KCN Mỹ Phước. Chủ hồ sơ  │ ││
│ │ GCN edit     │  │ │ đã nộp bản vẽ + giấy phép KD │ ││
│ │ SLA: 4d      │  │ │ + cam kết môi trường. Hiện   │ ││
│ │              │  │ │ chờ ý kiến về việc có phải  │ ││
│ │ [▸ Normal]   │  │ │ thẩm duyệt PCCC không.       │ ││
│ │ C-...-0003  │  │ │                               │ ││
│ │ ĐKKD corp    │  │ │ Câu hỏi cụ thể: Theo NĐ      │ ││
│ │ SLA: 5d      │  │ │ 136/2020 Điều 13, công trình │ ││
│ │              │  │ │ diện tích 500m² thuộc diện  │ ││
│ │              │  │ │ nào cần thẩm duyệt PCCC?    │ ││
│ │              │  │ │                               │ ││
│ │ ── Replied ──│  │ │ Pháp lý liên quan:           │ ││
│ │ C-...-9998  │  │ │ • NĐ 136/2020 Điều 13 [view] │ ││
│ │ C-...-9997  │  │ │ • QCVN 06:2022/BXD     [view] │ ││
│ │              │  │ │ • Luật PCCC 2001 Điều 15     │ ││
│ │              │  │ │                               │ ││
│ │              │  │ │ Precedent cases (3):         │ ││
│ │              │  │ │ • C-20250120-0042 [review]   │ ││
│ │              │  │ │ • C-20250318-0091 [review]   │ ││
│ │              │  │ │ • C-20250530-0117 [review]   │ ││
│ │              │  │ │                               │ ││
│ │              │  │ │ Documents attached:           │ ││
│ │              │  │ │ • ban_ve.pdf      [preview]   │ ││
│ │              │  │ │ • cam_ket_mt.pdf  [preview]   │ ││
│ │              │  │ └───────────────────────────────┘ ││
│ │              │  │                                  ││
│ │              │  │ ┌─ Opinion (your reply) ───────┐ ││
│ │              │  │ │ [rich text editor]            │ ││
│ │              │  │ │                               │ ││
│ │              │  │ │ Based on NĐ 136/2020 Điều 13.2│ ││
│ │              │  │ │ điểm b, công trình trên 300m² │ ││
│ │              │  │ │ tại khu công nghiệp phải thẩm│ ││
│ │              │  │ │ duyệt PCCC. Đề nghị chủ hồ sơ│ ││
│ │              │  │ │ liên hệ Phòng Cảnh sát PCCC...│ ││
│ │              │  │ │                               │ ││
│ │              │  │ │ [Cite NĐ 136/2020] [Cite QCVN]││
│ │              │  │ └───────────────────────────────┘ ││
│ │              │  │                                  ││
│ │              │  │ Decision: [Approve ✓] [Deny ✗]  ││
│ │              │  │ [Lưu nháp] [Gửi opinion]        ││
│ └──────────────┘  └────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

### Key features

- **Left list** (320px): ConsultRequest cards sorted by priority (urgent first) then SLA. Each card shows case ID, TTHC, SLA countdown với [design-tokens.md SLA color transition](./design-tokens.md#5-elevation--shadow-tokens), classification badge, unread dot. "── Replied ──" divider below pending.
- **Right detail panel** (flex): 3 stacked sections
  - **Pre-analyzed context** — auto-populated by Consult Agent (triggers LegalLookup + Summarizer on request creation): case summary, specific question, legal refs (clickable → KG Explorer), precedent cases (clickable → mini Document Viewer), attached docs (clickable → preview)
  - **Opinion composer** — rich text editor (Tiptap) with citation-insert buttons. Autosave every 5s.
  - **Decision** — Approve / Deny radio (affects how Tuấn's Compliance Workspace surfaces the opinion)
- **Realtime:** `consult_request` WS event appends card with slide-in + counter-animate unread badge + subtle notification sound (respecting system volume). `opinion_received` when a different pháp chế user responds — (optional, for future presence indicator).
- **Keyboard:** `j`/`k` navigate list, `Enter` open detail, `⌘+Enter` submit opinion, `⌘+S` save draft.

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §9](./artifact-inventory.md#9-consult-inbox-new):
- **MUST:** #12 ConsultRequest, #13 Opinion, #27 Pre-analyzed context, #8 Citation refs, #28 Precedent cases, #11 SLA countdown, #5 Classification badge
- **SHOULD:** #2 Document preview, #3 ExtractedEntity, #16 Summary

### Loading / skeleton

```
┌──────────────┐  ┌────────────────────────────────┐
│ ▒▒▒▒▒▒▒▒▒▒▒ │  │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │
│ ▒▒▒▒▒▒▒▒▒   │  │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒              │
│              │  │                                  │
│ ▒▒▒▒▒▒▒▒▒▒  │  │ ┌──────────────────────────────┐│
│ ▒▒▒▒▒▒      │  │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││
│              │  │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││
│ ▒▒▒▒▒▒▒▒▒▒  │  │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││
│ ▒▒▒▒▒▒      │  │ │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒           ││
│              │  │ └──────────────────────────────┘│
└──────────────┘  └────────────────────────────────┘
```

SSR renders empty left list shell. On mount: `consult:list` WS subscribe → list hydrates card-by-card với stagger 50ms. Detail panel stays empty until first card clicked. Pre-analyzed context skeleton shimmer 1.5s loop per section while Consult Agent enrichment completes.

### States

- **Empty:** No pending requests — "Tất cả consult đã được xử lý. Nghỉ ngơi một chút, anh Dũng ☕" illustration + last-7-days stats
- **Loading:** Skeleton above
- **Error (list fetch failed):** Retry button + contact IT link
- **Error (submit failed):** Keep opinion draft, show retry toast, highlight form
- **Focus:** Keyboard-focused card has `--color-border-focus` ring; active card has left-border accent stripe
- **Hover:** List item bg-surface-card-hover
- **Disabled submit:** When opinion textarea empty — button at `--color-action-disabled`, tooltip "Cần nhập ý kiến trước khi gửi"

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| WS disconnect | Top banner "Kết nối mất. Đang kết nối lại..." + draft stays cached | Auto-reconnect + toast on success |
| Submit timeout | Toast + retry button + draft preserved in localStorage | Retry or copy-paste elsewhere |
| Document preview fails | Inline "Xem trực tiếp" fallback link | Open in new tab |
| Precedent fetch fails | Section collapses with "Không tải được precedent cases [retry]" | Retry button |

### Demo hook

Not on main 2:30 storyboard critical path (which focuses on Tuấn/Hương/Quốc demo flow), but a judge Q&A will almost certainly ask: *"Consult loop hoạt động thế nào? Pháp chế nhận yêu cầu ra sao?"* This screen is the live answer — demonstrates end-to-end human-in-the-loop for Persona 5.

---

## 10. KG Explorer — Vietnamese Legal Knowledge Graph

### Purpose

Interactive explorer cho Knowledge Graph pháp luật Việt Nam. Chứng minh **legal reasoning is grounded, not hallucinated** — khi Compliance báo "thiếu PCCC theo NĐ 136/2020 Điều 13", user click citation → KG Explorer mở → shows that article trong context (parent decree, related articles, amendment history, TTHCs that require it). Không có screen này, GraphRAG claim chỉ là text.

Technical implementation đã specced đầy đủ ở [graph-visualization.md §Cytoscape KG Explorer](./graph-visualization.md#cytoscapejs--kg-explorer). Screen này là UX spec + layout shell để bọc nó.

### Routes
- `/kg` — top-level Vietnamese legal corpus overview (50 most-cited articles + decree index)
- `/kg/article/[article_id]` — zoom to a specific article's neighborhood
- `/kg/tthc/[tthc_code]` — zoom to TTHC spec subgraph (which articles this TTHC REQUIRES)
- `/kg/law/[law_id]` — zoom to full law structure (articles, chapters, amendments)

### Layout

```
┌──────────────────────────────────────────────────────────┐
│ [nav] Bản đồ pháp luật    [⌘K search] [⚙] [? help]     │
├──────────────────────────────────────────────────────────┤
│ Breadcrumb: Luật XD 2014 › Chương V › Điều 95           │
├────────────┬───────────────────────────────┬───────────┤
│            │                                 │            │
│ 🔍 Tìm kiếm│                                 │ Chi tiết:  │
│ [_________]│                                 │            │
│            │                                 │ NĐ 136/2020│
│ Filter:    │      [Cytoscape canvas]         │ /NĐ-CP     │
│ [x] Active │                                 │ Điều 13    │
│ [ ] Super  │    ●─────● NĐ 136/2020          │            │
│ [x] 📜 Law │   /  \   /  \                   │ "Về phòng  │
│ [x] 📖 Art │  ●    ●─●    ●                  │ cháy chữa  │
│ [x] ⚙ TTHC│  │   /│\│   /                   │ cháy..."   │
│            │  ●──● ●─●──●                    │            │
│ Clearance: │   \   │  /                      │ [serif     │
│ [▼ Confid.]│    ●──●                         │  Source    │
│            │                                 │  Serif 4   │
│ Saved:     │  ┌─ Minimap ──┐                │  16/26     │
│ • NĐ 136   │  │            │                │  full text]│
│ • Luật XD  │  └────────────┘                │            │
│ • QCVN 06  │  [fit] [+] [-] [reset] [TB|LR] │ References:│
│            │                                 │ → Luật PCCC│
│ Recent:    │                                 │   2001 Đ.4 │
│ • Điều 95  │                                 │ → QCVN 06  │
│ • Điều 13  │                                 │            │
│ • Điều 41  │                                 │ Amendments:│
│            │                                 │ NĐ 50/2024 │
│            │                                 │ (hiệu lực  │
│            │                                 │  01/07/24) │
│            │                                 │            │
│            │                                 │ TTHCs that │
│            │                                 │ REQUIRE:   │
│            │                                 │ • CPXD     │
│            │                                 │ • CPPCCC   │
│            │                                 │            │
│            │                                 │ Cases      │
│            │                                 │ citing:    │
│            │                                 │ 847 cases  │
│            │                                 │ [view]     │
└────────────┴───────────────────────────────┴───────────┘
```

- **Left sidebar (280px):** search, classification filter, saved views, recent history
- **Center (flex):** Cytoscape canvas full-bleed, dark inset surface. Bottom-left minimap + layout/zoom controls.
- **Right panel (360px, collapsible via keyboard `]` or header toggle):** node detail — full article text rendered in Source Serif 4 16/26, amendment chain, related TTHCs, precedent cases citing this article.

### Key interactions

- **Click node** → right panel hydrates + auto-expand 1-hop neighbors (fade-in 250ms, dagre re-layout animated 400ms)
- **Shift-click** → multi-select → "So sánh" comparison panel slides up from bottom
- **Right-click** → context menu: pin node, hide neighbors, export subgraph as PNG/JSON
- **Hover edge** → tooltip showing edge type (`SUPERSEDED_BY`, `REFERENCES`, `REQUIRED_BY`, `AMENDS`) + date range
- **Keyboard:**
  - `/` focus search
  - `Esc` clear selection
  - `F` fit to screen
  - `[` `]` collapse/expand right panel
  - `1-4` classification filter presets
  - `Ctrl+Z` undo last expand (frequent navigation)
- **Layout toggle** top toolbar: Cola force-directed (default, shows topology) ↔ Dagre TB (shows hierarchy for single law structure)

### Classification-aware rendering

Following [design-system.md Classification banner](./design-system.md) rules:
- Nodes at classification > user clearance render as ghost with `🔒 Clearance insufficient` placeholder (no text, no outgoing edges revealed)
- Top sticky banner shows highest-classified node currently on canvas: `UNCLASSIFIED` green or `CONFIDENTIAL` blue banner per [artifact-inventory.md #5](./artifact-inventory.md)
- Hover ghost node → tooltip "Yêu cầu clearance: Confidential. [Request elevation]"

### Lazy loading

- **Initial load:** 50 most-cited articles + 20 TTHCs as seed graph (≤200ms render target)
- **Click-to-expand:** on node click, fetch 1-hop neighbors from GDB (batched, returns ≤30 new nodes), animate in with stagger 50ms
- **Max visible:** 500 nodes → beyond that, cluster by decree (single Law node replaces its Articles, click to decompose)
- **Search results:** always shown as floating "search result cards" above canvas with "Zoom to" button — never teleport camera without confirmation

### Artifacts surfaced

Per [artifact-inventory.md Table 2 §10](./artifact-inventory.md#10-kg-explorer-new):
- **MUST:** #29 Law subgraph, #9 Article text, #8 Citation navigation, #5 Classification filter
- **SHOULD:** TTHC→Article `REQUIRES` edges (static KG data), search/filter, saved views
- **MAY:** Mini version embeddable in Compliance Workspace legal panel (phase 2)

### Loading / skeleton

```
┌────────────┬───────────────────────────────┬───────────┐
│ ▒▒▒▒▒▒▒▒▒ │                                 │ ▒▒▒▒▒▒▒▒▒│
│           │     ●─ ─ ─●                     │           │
│ ▒▒▒▒▒▒▒▒ │    /       \                    │ ▒▒▒▒▒▒▒▒▒│
│ ▒▒▒▒▒▒   │   ●         ●                   │ ▒▒▒▒▒▒▒▒▒│
│           │    \       /                    │           │
│ ▒▒▒▒▒▒▒▒ │     ●─ ─ ─●                     │ ▒▒▒▒▒▒▒▒▒│
│           │                                 │ ▒▒▒▒▒▒▒▒▒│
│           │   (5 placeholder nodes          │           │
│           │    with dashed borders +       │ ▒▒▒▒▒▒▒▒▒│
│           │    shimmer loop while           │           │
│           │    seed graph loads)           │           │
└────────────┴───────────────────────────────┴───────────┘
```

Render order:
1. Shell (nav, sidebar, right panel frame) — SSR
2. Seed graph API fetch (~100 nodes) — CSR
3. Initial Cola layout animation (600ms)
4. User interacts

### States

- **Empty (no search results):** "Không tìm thấy điều luật khớp. Thử tìm theo: số hiệu (NĐ 136/2020), từ khóa (phòng cháy), hoặc mã TTHC (1.004415)" + top-10 most-cited articles as suggestions
- **Loading:** Skeleton above
- **Error:** API fail banner with retry + link to KG Explorer docs
- **Classification-filtered:** Some nodes ghost with 🔒 indicator (see above)
- **Out of date data:** If KG last updated > 7 days, top banner "Dữ liệu pháp luật cập nhật: [date]. [Làm mới]"

### Error states (specific)

| Error | UI pattern | Recovery |
|---|---|---|
| GDB query timeout | Toast "Truy vấn chậm, thử giới hạn phạm vi" + retry | Reduce depth or cluster |
| Cytoscape render fails on low-end device | Fallback to list view with outgoing edges as indentation | Toggle available in settings |
| Clearance fetch fails | All nodes at classification > Unclassified ghost out | Banner explains + retry |

### Demo hook

Scene 3 (1:00-1:05) voiceover mentions *"LegalLookup dùng Agentic GraphRAG, graph traversal qua GDB"* — this screen is what judges can click through AFTER the video during live Q&A to verify claim. Also the primary demo surface for Q&A questions: *"Cho tôi xem NĐ 136/2020 Điều 13"* → Anh Dũng navigates live → judges see the law exist in the graph with real text excerpts.

**Optional extension for video:** 10-second B-roll cutting from Scene 3 showing KG Explorer zooming from seed graph into NĐ 136/2020 → Điều 13 as voiceover mentions it.

---

## Screen priority for build

Day 14 (full day — 8h):
1. Citizen Portal — home + tracking (6h)
2. Intake UI (4h) [parallel w/ above via 2 devs]
3. Agent Trace Viewer (8h — **hero #1 signature**)

Day 15 (full day — 10h):
4. Compliance Workspace (6h)
5. **Consult Inbox (4h — NEW, critical)**
6. Department Inbox (3h)
7. Document Viewer (3h)

Day 15 evening + Day 16 morning:
8. Leadership Dashboard (5h)
9. Security Console (6h — 3 permission scenes harness)
10. **KG Explorer (5h — NEW, critical for legal reasoning demo)**

Day 16 afternoon + evening:
- End-to-end dry run with mocked WS data
- Cross-screen navigation polish
- Demo video production rehearsal (screen recording)

Day 17:
- Demo video final cut
- Submission package

**Total: ~60h across frontend team (likely 2 devs = 30h each over 3.5 days).** Reuse heavily per [design-system.md Implementation references](./design-system.md#implementation-references-reuse-first) — budget 3h average per screen; anything over must be downgraded or swapped for a shadcn/Tremor block.

All 10 screens polished by end of day 16, demo video day 17.
