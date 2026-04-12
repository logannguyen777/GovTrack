# Demo Day Mechanics — Seed data, reset, fallback

> Operational runbook for the live pitch on **April 26, 2026**. This doc covers everything that makes the demo reproducible: hero case seed data, reset endpoints, fallback video trigger, projector test, rehearsal protocol.
>
> **Read order:** demo lead reads this end-to-end before rehearsals. Frontend lead verifies seed data matches screen specs. Presenter memorizes the fallback plan.

---

## 1. Hero case seed data — C-20260412-0001

The entire 2:30 demo narrative uses **one hero case**. All 8 scenes reference it, every screen must have mock data that matches these values exactly. Any drift means voiceover doesn't match what's on screen.

### Case metadata

```yaml
case_id: C-20260412-0001
tthc_code: "1.004415"
tthc_name: "Cấp giấy phép xây dựng"
created_at: "2026-04-12T14:30:00+07:00"
status: "pending_citizen"  # initial state for Scene 2-4
applicant:
  id: applicant_hero_001
  full_name: "Nguyễn Văn Minh"
  display_name: "Nguyễn Văn M***"  # masked for Confidential classification
  national_id: "079123456789"
  masked_national_id: "079****6789"
  phone: "0909123456"
  email: "nguyenvanminh.demo@example.vn"
classification: "confidential"  # assigned by SecurityOfficer at t=18s in Scene 3
classification_reason: "Công trình gần khu công nghiệp có cơ sở hạ tầng trọng yếu"
organization:
  dept_code: "SXD-BD"
  dept_name: "Sở Xây dựng tỉnh Bình Dương"
  office: "Phòng Quản lý xây dựng"
project:
  type: "Nhà xưởng công nghiệp"
  area_m2: 500
  location_text: "Lô B3, Khu công nghiệp Mỹ Phước III, huyện Bến Cát"
  location_coordinates: [11.1245, 106.6180]
  location_masked: "KCN Mỹ Phước, Bình Dương"  # shown to Unclassified viewers
  near_military: true  # triggers Confidential
```

### Documents bundle

```yaml
documents:
  - filename: don_cpxd.pdf
    label: "Đơn đề nghị cấp phép xây dựng"
    mime: application/pdf
    ocr_status: complete
    entities:
      - { type: "chủ hồ sơ", value: "Nguyễn Văn M***" }
      - { type: "loại TTHC", value: "Cấp phép XD nhà xưởng" }

  - filename: gcn_qsdd.jpg
    label: "Giấy chứng nhận quyền sử dụng đất"
    mime: image/jpeg
    ocr_status: complete
    entities:
      - { type: "số GCN", value: "AL 123456" }
      - { type: "diện tích", value: "500m²" }
      - { type: "vị trí", value: "Lô B3, KCN Mỹ Phước" }
      - { type: "con dấu đỏ", value: true }

  - filename: ban_ve.pdf
    label: "Bản vẽ thiết kế"
    mime: application/pdf
    ocr_status: complete
    entities:
      - { type: "tỉ lệ", value: "1:200" }
      - { type: "diện tích", value: "500m² (khớp)" }

  - filename: cam_ket_mt.pdf
    label: "Cam kết bảo vệ môi trường"
    mime: application/pdf
    ocr_status: complete
    entities:
      - { type: "loại dự án", value: "sản xuất công nghiệp" }

  - filename: gp_kd.jpg
    label: "Giấy phép kinh doanh"
    mime: image/jpeg
    ocr_status: complete
    entities:
      - { type: "MST", value: "3700812345" }
      - { type: "ngành nghề", value: "sản xuất linh kiện điện tử" }

  # 6th document missing initially — this is the gap
  - filename: null
    label: "Văn bản thẩm duyệt PCCC"
    required: true
    status: missing
    added_after: "2026-04-20T09:00:00+07:00"  # added 8 days later, Scene 5
```

### Gap + citation chain

```yaml
gaps:
  - id: gap_001
    description: "Thiếu Văn bản thẩm duyệt PCCC"
    severity: blocker
    detected_at: "2026-04-12T14:31:45+07:00"  # t=18s in Agent Trace choreography
    citation:
      law: "Nghị định 136/2020/NĐ-CP"
      article: "Điều 13"
      clause: "khoản 2"
      point: "điểm b"
      text_excerpt: "Công trình có tổng diện tích sàn từ 300m² trở lên tại khu công nghiệp, khu chế xuất, cụm công nghiệp thuộc danh mục phải thẩm duyệt thiết kế về phòng cháy và chữa cháy."
    location_of_authority: "Phòng Cảnh sát PCCC và CNCH - Công an tỉnh Bình Dương"
    estimated_time: "~10 ngày làm việc"
```

### Agent step history (for replay mode)

```yaml
agent_steps:
  - agent: Planner
    started_at: "2026-04-12T14:30:30+07:00"
    latency_ms: 892
    tokens_in: 450
    tokens_out: 120
    output:
      parallel:
        - DocAnalyzer
        - SecurityOfficer
        - Classifier

  - agent: DocAnalyzer
    started_at: "2026-04-12T14:30:32+07:00"
    latency_ms: 3420
    tokens_in: 8500
    tokens_out: 1200
    output:
      documents_processed: 5
      entities_extracted: 12

  - agent: Classifier
    started_at: "2026-04-12T14:30:34+07:00"
    latency_ms: 145
    tokens_in: 380
    tokens_out: 45
    output:
      tthc_matched: "1.004415"
      confidence: 0.96

  - agent: SecurityOfficer
    started_at: "2026-04-12T14:30:32+07:00"
    latency_ms: 125
    tokens_in: 220
    tokens_out: 30
    output:
      classification: confidential
      reason: "near sensitive zone"

  - agent: Compliance
    started_at: "2026-04-12T14:31:10+07:00"
    latency_ms: 342
    tokens_in: 1240
    tokens_out: 86
    gremlin_query: |
      g.V().has('Case','id',$cid)
       .out('MATCHES_TTHC').out('REQUIRES')
       .where(not exists satisfied)
    output:
      gaps_found: 1
      gap_id: gap_001

  - agent: LegalLookup
    started_at: "2026-04-12T14:31:45+07:00"
    latency_ms: 420
    tokens_in: 680
    tokens_out: 220
    output:
      citation: "NĐ 136/2020 Điều 13.2.b"
      article_text: "Công trình có tổng diện tích sàn từ 300m²..."

  # continued for Router, Consult, Summarizer, Drafter on day 10 (Scene 5)
```

### Consult request + opinion (Scene 5)

```yaml
consult_request:
  id: consult_001
  case_id: C-20260412-0001
  from_user: tuan_compliance
  to_dept: phap_che
  assigned_to: dung_phap_che
  created_at: "2026-04-20T09:15:00+07:00"
  pre_analyzed_context:
    summary: "Công trình 500m² tại KCN Mỹ Phước. Chủ hồ sơ đã nộp bản vẽ + GPKD + cam kết MT."
    question: "Công trình có diện tích 500m² tại KCN thuộc diện phải thẩm duyệt PCCC theo NĐ 136/2020 Điều 13 không?"
    legal_refs:
      - "NĐ 136/2020 Điều 13"
      - "QCVN 06:2022/BXD"
    precedent_cases:
      - C-20250120-0042
      - C-20250318-0091
      - C-20250530-0117

opinion:
  id: opinion_001
  consult_id: consult_001
  author: dung_phap_che
  created_at: "2026-04-20T10:42:00+07:00"
  decision: approve
  text: |
    Theo NĐ 136/2020 Điều 13 khoản 2 điểm b, công trình có tổng diện tích sàn
    từ 300m² trở lên tại khu công nghiệp phải thẩm duyệt thiết kế về PCCC.
    Công trình 500m² của chủ hồ sơ thuộc diện này, cần bổ sung Văn bản thẩm
    duyệt trước khi cấp phép. Đề xuất thông báo công dân bổ sung và xử lý
    song song các điều kiện còn lại.
```

### Decision + publish (Scene 6)

```yaml
decision:
  case_id: C-20260412-0001
  decision: approve
  approved_by: huong_leadership
  approved_at: "2026-04-22T14:30:00+07:00"

published_doc:
  doc_number: "SXD-BD/QĐ-2026/1847"
  doc_type: "Quyết định cấp phép xây dựng"
  published_at: "2026-04-22T14:32:00+07:00"
  qr_verify_url: "https://govflow.vn/verify/abc123def456"
  signed_by:
    - role: "Phó Giám đốc Sở"
      name: "Trần Thị Hương"
      digital_signature_hash: "sha256:7f3a9c..."
```

### Users (for demo accounts)

```yaml
users:
  - username: lan_intake
    full_name: "Trần Thị Lan"
    role: intake_officer
    dept: SXD-BD
    clearance: unclassified

  - username: tuan_compliance
    full_name: "Lê Văn Tuấn"
    role: compliance_officer
    dept: SXD-BD
    clearance: confidential

  - username: huong_leadership
    full_name: "Trần Thị Hương"
    role: deputy_director
    dept: SXD-BD
    clearance: secret

  - username: quoc_security
    full_name: "Phạm Văn Quốc"
    role: security_officer
    dept: SXD-BD
    clearance: topsecret

  - username: dung_phap_che
    full_name: "Nguyễn Văn Dũng"
    role: legal_specialist
    dept: SXD-BD-PhapChe
    clearance: confidential

  - username: minh_citizen
    full_name: "Nguyễn Văn Minh"
    role: citizen
    vneid_verified: true
```

---

## 2. Demo mode & reset endpoint

### Demo mode environment variable

```bash
GOVFLOW_DEMO_MODE=true    # enables demo-specific fixtures + reset endpoint
GOVFLOW_DEMO_SEED=hero_case_001  # which seed to load
```

When `GOVFLOW_DEMO_MODE=true`:
- Database auto-seeds hero case on startup
- Reset endpoint `/demo/reset` is exposed (protected by demo token)
- Permission demo scenarios (Scene A/B/C) are triggerable via `/demo/scene/:id`
- User auth bypassed for demo users (VNeID mock)
- WebSocket topics pre-subscribed for the hero case
- "Demo Mode" badge visible in app header (so nobody confuses demo with prod)

### Reset endpoint

```
POST /demo/reset
Authorization: Bearer ${GOVFLOW_DEMO_TOKEN}

Body: {
  "seed": "hero_case_001",     // which seed to reload
  "scenes": ["all"],            // or ["scene_2", "scene_3"] etc
  "reset_users": true           // clear user elevation grants
}

Response: {
  "status": "reset",
  "seed_loaded": "hero_case_001",
  "case_id": "C-20260412-0001",
  "timestamp": "2026-04-26T09:00:00+07:00"
}
```

**Who triggers:** demo lead runs this between rehearsals AND 5 minutes before the actual pitch. Endpoint is also accessible via a button in `/admin/demo` for convenience (hidden from regular users).

**What it resets:**
- Hero case back to `pending_citizen` status (so Scene 2 can replay)
- All agent steps cleared
- All audit events for hero case cleared
- Any user clearance elevations revoked
- Consult requests + opinions cleared
- Published doc cleared
- Seed data re-loaded from YAML

**What it DOES NOT reset:**
- Other cases in the system (preserved for "what else is there" Q&A)
- User accounts themselves (just their ephemeral state)
- Static legal KG (never changes at runtime)

### Replay modes

Demo mode supports 3 playback speeds:

```
GOVFLOW_DEMO_SPEED=1x    # natural speed (default, what judges see)
GOVFLOW_DEMO_SPEED=0.5x  # half speed for rehearsal debugging
GOVFLOW_DEMO_SPEED=2x    # fast forward for quick dry runs
```

Speed affects agent step delays (mock backend inserts waits between steps).

---

## 3. Fallback plan — live demo fails

### Decision tree

```
Live demo starts at t=0 (presenter clicks "Start demo")
  │
  ├─ t+5s: WS not connected?
  │         → Presenter sees red banner in app header
  │         → Presenter says: "Chúng ta chuyển sang bản ghi hình để tiết kiệm thời gian"
  │         → Switch to video
  │
  ├─ t+15s: Scene 2 not progressing (OCR not completing)?
  │         → Presenter waits max 3 seconds
  │         → Says: "Hệ thống đang xử lý chậm, xem bản ghi hình demo đầy đủ"
  │         → Switch to video from Scene 2
  │
  ├─ t+60s: Scene 3 (Agent Trace) not building up?
  │         → Presenter continues narration
  │         → Waits max 5 seconds
  │         → Switch to video IF Gap hasn't appeared by t=75s
  │
  ├─ Scene 7 (Security) fails to trigger?
  │         → Scene 7 video is a separate clip — play just that
  │         → Say: "Đây là bản ghi hình 15 giây của demo security"
  │
  └─ Live demo succeeds end-to-end
            → Switch to slides for impact numbers (Scene 8)
```

### Fallback video files

Pre-produced videos stored at `/home/logan/GovTrack/assets/demo-videos/`:

| File | Scenes | Duration | Purpose |
|---|---|---|---|
| `full-demo-2-30.mp4` | 1-8 | 2:30 | Complete fallback if everything fails |
| `scene-2-intake.mp4` | 2 only | 25s | If Scene 2 fails mid-pitch |
| `scene-3-agent-trace.mp4` | 3 only | 25s | If Scene 3 Agent Trace fails |
| `scene-6-publish.mp4` | 6 only | 15s | If Drafter/Publish fails |
| `scene-7-security.mp4` | 7 only | 15s | If permission harness fails |

**Specs:** 1920×1080, H.264, 30fps, AAC audio, burned-in VN + EN subtitles.

### Transition script (memorize)

When switching to fallback video, presenter says (calmly, no panic):

> **"Để tiết kiệm thời gian, em/tôi xin phép chuyển sang bản ghi hình demo đã chuẩn bị."**

Press hotkey `⌘⌥V` (or whatever is bound on demo laptop) to swap the on-screen view from browser → media player with fallback video queued.

**DO NOT say:**
- ❌ "Xin lỗi, hệ thống đang bị lỗi"
- ❌ "Normally this works but..."
- ❌ Long technical explanation

**DO say:**
- ✅ "Để minh họa tốt hơn, em chuyển sang video đã chuẩn bị"
- ✅ Smile, confident, move forward

Rehearse the switch 3 times before the actual pitch.

---

## 4. Projector & rendering test

### Resolution check

- **Demo laptop:** 1440×900 (MacBook Air 13) or 1920×1080 (Dell XPS 15)
- **Projector output:** 1920×1080 most likely, sometimes 1280×720
- **UI target:** `xl: 1280px` and `2xl: 1536px` per [design-system.md breakpoints](./design-system.md)

### Rendering checklist (run on actual demo laptop + projector)

- [ ] Open hero case in Agent Trace Viewer at 1920×1080 projector resolution
- [ ] Verify all 10 timeline rows visible without scrolling
- [ ] Verify graph fits with padding, MiniMap not clipped
- [ ] Classification banner visible at top + bottom without overlapping content
- [ ] Compliance bar in Intake UI is legible at projector distance (6-8m from audience)
- [ ] Vietnamese diacritics render cleanly — no pixelation on `ẩ`, `ệ`, `ằ` at both resolutions
- [ ] Tabular numbers in Audit Log align in columns
- [ ] Dark theme contrast: all text ≥ 4.5:1 on real projector (dim rooms exaggerate low contrast)
- [ ] Graph node borders visible (1px can disappear on cheap projectors — may need 1.5px override)
- [ ] Hero case PDF (published) renders all pages at 1x zoom, QR code scannable at projector

### Font rendering test

Render the [Vietnamese canonical test paragraph](./design-tokens.md#canonical-vietnamese-test-paragraph) at:
- 14/23 (dashboard body)
- 16/26 (reading body)
- 24/30 (heading)

Check on actual projector in dim room. If any diacritic collides or any letter pixelates, abort demo on that device and fall back to laptop-only mode.

### Color test

- Dark background `--color-surface-page` (OKLCH 0.14) should look **dark charcoal, not blue-tinted** on projector
- Classification banner colors must be instantly recognizable (UNCLASSIFIED green vs CONFIDENTIAL blue vs SECRET orange)
- Red denied-access flash must be visible at 6-8m distance (not washed out)

### Known projector issues

- **Cheap LCD projectors** crush dark colors — levels 1-3 of any ramp may become indistinguishable. Mitigation: bump surface colors up one step in demo mode.
- **Dim projectors** wash out amber/yellow — our gap amber might read as tan. Mitigation: use amber step-10 instead of step-9 for demo mode.
- **HDMI color space mismatch** can make OKLCH look off. Run a color bar test pattern before demo to verify calibration.

---

## 5. Rehearsal protocol

### T-7 days (April 19)
- Full dry run with mocked backend data
- Record video of dry run for self-review
- Identify timing drift vs storyboard (voice over-pacing or under-pacing UI)
- Fix top 3 issues

### T-3 days (April 23)
- End-to-end dry run with real backend (or high-fidelity mocks)
- Test on demo laptop
- Test fallback video transitions
- Record final dry run

### T-1 day (April 25)
- Dry run AT the venue with actual projector
- Color calibration, font rendering check
- Fallback video files staged on demo laptop (not cloud — must work offline)
- Network failure drill (unplug WiFi, verify fallback triggers)

### Demo day (April 26)
- Arrive 1 hour early
- Run demo reset 5 minutes before go-live
- Warm up WebSocket connections
- Confirm user auth mocks loaded
- Test ⌘K command palette
- Final fallback video check
- Glass of water, deep breath, go

### Post-demo
- Save logs for troubleshooting if needed
- Reset demo state for next round (if back-to-back pitches)

---

## 6. Team roles on demo day

| Role | Responsibility |
|---|---|
| **Presenter** | Speaks, operates demo UI, handles Q&A |
| **Demo operator** (optional) | Behind the laptop, runs reset, triggers fallback video, watches for errors |
| **Pitch lead** | Monitors timing, signals if off-pace |
| **Tech lead** | On standby with backend logs, emergency hotfix if allowed |

For solo presenter (most likely scenario): memorize fallback hotkey, practice operating demo while speaking, have water nearby.

---

## 7. Related files

- [screen-catalog.md](./screen-catalog.md) — screen specs referenced by seed data
- [artifact-inventory.md](./artifact-inventory.md) — Table 3 maps demo timestamps to artifacts
- [realtime-interactions.md](./realtime-interactions.md) — WS event subscription plan for demo
- [07-pitch/demo-video-storyboard.md](../07-pitch/demo-video-storyboard.md) — narrative storyboard this implements
- [07-pitch/rehearsal-protocol.md](../07-pitch/rehearsal-protocol.md) — higher-level rehearsal plan (pitch team, not UI)
