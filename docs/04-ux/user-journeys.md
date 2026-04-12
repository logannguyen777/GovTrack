# User Journeys — 5 personas × 5 TTHC

End-to-end journey per persona for each major TTHC. These are what the UX must support — not just individual screens, but full flows.

## Primary journey — Anh Minh × CPXD (Cấp phép xây dựng)

This is the headline demo. Full detail.

### Day 0 — Submission
1. Anh Minh opens smartphone, goes to Citizen Portal
2. Taps "Nộp hồ sơ mới"
3. Selects "Cấp giấy phép xây dựng"
4. VNeID authentication → business login
5. Wizard shows required docs list (6 items)
6. Taps "Bắt đầu upload"
7. Camera capture or file select for each doc
8. Each file uploads, gets OCR preview (green check ✓)
9. Taps "Nộp"
10. Gets case code: `C-20260412-0001`
11. Sees tracking page with "Đang phân tích"

### Day 0 — 2 minutes later
12. Backend agents process. Compliance finds missing PCCC.
13. Drafter generates citizen notice: "Thiếu văn bản thẩm duyệt PCCC..."
14. Push notification to Anh Minh's phone
15. Anh Minh taps notification → opens tracking page
16. Sees detailed explanation with:
   - What's missing
   - Why (NĐ 136/2020 Điều 13 — công trình 500m² tại KCN)
   - Where to get it (Phòng Cảnh sát PCCC Bình Dương with address + phone)
   - Expected time (~10 days)
   - Upload slot right there

### Day 0-10 — Getting PCCC
17. Anh Minh contacts Cảnh sát PCCC
18. Submits PCCC request (outside GovFlow — separate system)
19. Gets văn bản thẩm duyệt PCCC on day 8
20. Returns to GovFlow tracking page
21. Uploads the new document
22. Sees "Đang tiếp tục xử lý"

### Day 8-10 — Processing continues
23. Compliance re-checks → all complete
24. Router assigns to Phòng Quản lý XD
25. Consult Pháp chế + Quy hoạch (automatic)
26. Summarizer creates executive summary
27. Anh Minh sees status updates in realtime: "Pháp chế đã duyệt", "Quy hoạch đã duyệt", "Đang chờ phê duyệt lãnh đạo"

### Day 10 — Leadership approval
28. Chị Hương opens Leadership Dashboard
29. Sees C-20260412-0001 in approve queue with 100% compliance
30. Reviews executive summary + 1 click approve
31. Drafter generates Giấy phép XD document
32. Chị Hương reviews draft, clicks "Ký và phát hành"
33. Signed PDF uploaded to OSS, PublishedDoc created
34. Notification sent to Anh Minh

### Day 10 — Receiving result
35. Anh Minh gets push: "Giấy phép của bạn đã sẵn sàng"
36. Opens tracking page
37. Sees "Đã cấp phép" with green check
38. Taps download → signed PDF
39. Also gets QR code to verify authenticity
40. Done. 10 days total (vs 30-90 days before) with only 1 trip for PCCC.

### Time saved
- Before: 30-90 days, 3-5 in-person trips
- After: 10 days, 1 trip (just for PCCC which is external)
- **80%+ time saved, 70%+ trip reduction**

---

## Journey — Chị Lan × Bộ phận Một cửa (front desk)

### Daily flow — receiving citizens in person

1. Chị Lan starts shift at 8am, opens Intake UI
2. First citizen arrives with paper bundle
3. Chị Lan:
   - Places documents on document scanner (or uses camera)
   - Files upload to GovFlow
   - In ~30 seconds, Qwen3-VL OCRs + DocAnalyzer extracts
4. Intake UI shows:
   - Auto-detected TTHC: "Cấp phép XD" (confidence 94%)
   - Auto-filled metadata from OCR
   - Compliance check: 80% (missing 1 item)
5. Chị Lan confirms TTHC (click confirm)
6. System creates Case + generates code
7. Chị Lan prints biên nhận (receipt with QR code for citizen)
8. Citizen gets told about missing item verbally + written on receipt
9. Citizen leaves with clear instructions
10. Chị Lan moves to next citizen

### Time saved
- Before: 15-20 minutes per citizen (manual check + data entry)
- After: 3-5 minutes per citizen
- **3-4× throughput, less tired, fewer errors**

---

## Journey — Anh Tuấn × Compliance review

### Morning review

1. Anh Tuấn opens Department Inbox at 8am
2. Kanban shows: 3 Mới, 5 Compliance OK, 12 Đang xử lý, 4 Chờ consult, 2 Quyết định
3. Clicks "Compliance OK" column to start with easy ones
4. Opens first case C-20260412-0001
5. Compliance Workspace opens:
   - Documents column: 6 files, all green
   - Compliance checklist: 6/6 ✓
   - Legal panel: NĐ 15/2021 Điều 41 already cited
   - Summary (staff): 10 lines with key facts + open issues
6. Anh Tuấn scans through in 2 minutes (vs 15-30 minutes before)
7. Clicks "Đề xuất phê duyệt lãnh đạo"
8. System generates tờ trình draft automatically
9. Anh Tuấn reviews draft, adds 1 comment, saves
10. Moves to next case

### Complex case with consult need

1. Opens case C-20260412-0005 (SLA: 2 ngày remaining)
2. Compliance Workspace shows compliance 90%, 1 legal ambiguity flagged
3. Legal panel: LegalLookup found 3 potentially conflicting provisions
4. Anh Tuấn clicks "Xin ý kiến Pháp chế" → **Consult slide panel** opens from right (see [screen-catalog.md §4 Consult dialog spec](./screen-catalog.md#consult-dialog-slide-panel-spec))
5. Panel pre-fills with context from Consult agent:
   - Auto-summarized question referencing the 3 conflicting provisions
   - 3 legal refs pre-checked from LegalLookup output
   - Recipient dropdown suggests "Anh Dũng - Pháp chế (online)"
   - Expected response time: "2-4 giờ"
6. Anh Tuấn reviews, adjusts question, clicks "Gửi →"
7. Panel slides out, toast confirms, header now shows "⏳ Đang chờ ý kiến pháp chế" chip
8. Continues with other cases

### Later — Pháp chế response surfaces in Legal panel
9. Notification bell pulses + counter animates: "Anh Dũng đã trả lời ý kiến cho C-20260412-0005"
10. Click notification → Compliance WS opens at case, **Legal panel has new line item with pulse glow**: "💬 Pháp chế - Anh Dũng (2h trước): [opinion excerpt, click để xem]"
11. Anh Tuấn clicks → full opinion appears inline in Legal panel; Opinion vertex also visible as new node in Agent Trace Viewer if open
12. Pháp chế opinion aligned with his instinct → proceeds with approve recommendation

### Time saved
- Before: 30-60 minutes per case
- After: 5-15 minutes per case
- **5-10× throughput**

---

## Journey — Chị Hương × Leadership approval

### Morning review

1. Chị Hương opens Leadership Dashboard at 9am
2. Sees:
   - 1,247 active cases
   - 94% SLA hit rate (this week)
   - 8 overdue alerts
   - 15 cần ký (approval queue)
3. Clicks "8 overdue" first
4. Sees list with reasons
5. 3 are waiting on citizen (not her problem)
6. 3 are waiting on consult (escalates: "Pháp chế còn treo 5 yêu cầu")
7. 2 are waiting on her review
8. Opens first of the 2 → 1-click approve
9. Continues

### Batch approval
1. Back to dashboard, clicks "Cần ký (15)"
2. List view with compliance score per case
3. Filters: compliance >= 95% (safe to batch)
4. Selects 10 that meet criteria
5. Clicks "Ký loạt chọn"
6. Confirmation dialog: "Ký 10 văn bản? Tổng thời gian tiết kiệm: 50 phút"
7. Confirms with digital signature prompt (PKI)
8. Done. 10 giấy phép published in 30 seconds.

### AI Weekly Brief (pitch-worthy feature)
1. Chị Hương clicks "AI Weekly Brief ⚡"
2. Hologres AI Function calls Qwen3-Max inline:
   ```sql
   SELECT ai_generate_text('qwen-max', ...)
   FROM analytics_cases WHERE ...
   ```
3. Brief appears in 3 seconds:
   > "Tuần này Phòng QLXD xử lý 87 hồ sơ CPXD, 94% SLA hit. 3 cases overdue do vướng Pháp chế chờ 5 ngày. Anomaly: cấp phép cho dự án lớn > 10 ha tăng 30% so với tuần trước, có thể cần điều chỉnh workflow. Đề xuất: bàn với Pháp chế giảm SLA consult từ 7 ngày → 3 ngày."
4. 1-click export as PDF for báo cáo lãnh đạo cấp trên

### Time saved
- Before: 20-40 minutes per case to review + approve
- After: 2-5 minutes per case (or 30 seconds with batch)
- **10× faster approval, no rubber-stamping (still sees summary + compliance score)**

---

## Journey — Anh Dũng × Consult (Pháp chế)

### Consult request flow

1. At 8am, Anh Dũng sees notification on phone + bell badge on desktop: "3 consult requests mới"
2. Opens **[Consult Inbox](./screen-catalog.md#9-consult-inbox--chuyên-viên-pháp-chế--quy-hoạch)** at `/consult` — 2-column layout:
   - Left list: 3 pending cards sorted by SLA urgency (C-...-0005 "Urgent, SLA 2d" at top)
   - Right detail panel empty until he clicks a card
3. Clicks first card (C-...-0005) → detail panel hydrates:
   - **Pre-analyzed context** (auto-populated by Consult agent 5s after request creation): 3-line case summary, specific question from Tuấn highlighted, 3 legal refs pre-loaded with excerpts, 3 precedent cases listed (semantic similarity from Hologres Proxima), attached documents previewable
   - Classification banner: Confidential
4. Anh Dũng scans the pre-analyzed context in 3 minutes (vs 30 minutes to reconstruct manually)
5. **Drill-down when uncertain:** for 1 of the 3 precedent cases, he clicks "Review" → mini Document Viewer opens in modal showing how Compliance decided that case. For the conflicting legal provisions, he clicks a citation → **[KG Explorer](./screen-catalog.md#10-kg-explorer--vietnamese-legal-knowledge-graph)** opens in new tab showing the amendment chain of NĐ 15/2021 and identifying which version is currently in effect
6. Returns to Consult Inbox, writes opinion in Tiptap rich-text composer with citation-insert buttons: "Phù hợp với NĐ 15/2021 Điều 41 (bản hiện hành sau sửa đổi), đồng ý cấp phép. Lưu ý cần đảm bảo khoảng lùi theo QĐ quy hoạch địa phương."
7. Selects decision: Approve
8. Clicks "Gửi opinion" (or `⌘+Enter`)
9. System: writes Opinion vertex to Context Graph → fires WS event `opinion_received` on topic `case:C-...-0005` → Anh Tuấn's Compliance WS surfaces new line with pulse glow in Legal panel; Agent Trace Viewer (if open anywhere) gets new Opinion node
10. Anh Dũng's inbox card moves to "── Replied ──" section; list item fades; focus jumps to next pending card
11. Repeats for remaining 2 cases

### Time saved
- Before: 30-60 minutes per consult (reconstruct context + read laws + write opinion)
- After: 5-10 minutes
- **6× throughput, more accurate opinions** — grounded in LegalLookup + KG Explorer instead of memory

---

## Journey — Anh Quốc × Security monitoring

### Daily security check

1. Opens Security Console at 8am
2. Dashboard shows:
   - 12,345 audit events last 24h
   - 45 denied access (normal)
   - 3 anomalies detected
3. Reviews anomalies:
   - **Anomaly 1:** User 'xyz_1' had 12 denied access in 10 minutes
   - **Anomaly 2:** Access to Top Secret classification at 2am from non-standard IP
   - **Anomaly 3:** Agent 'LegalLookup' attempted to write Gap (out of scope)
4. For Anomaly 1: clicks "Review" → sees user attempted to access cases in another department
5. Disables user pending investigation, emails manager
6. For Anomaly 2: investigates — turns out to be legitimate (a deputy with elevated clearance working late)
7. For Anomaly 3: investigates — simulated scene during demo, no action needed

### Forensic investigation (when incident happens)

1. Incident: "Khiếu nại về case C-20260412-0001 bị xử lý thiên vị"
2. Anh Quốc opens case in Security Console
3. Replays full audit trail:
   ```
   14:30 user:chi_lan   create Case C-001
   14:31 agent:Classifier write MATCHES_TTHC
   14:32 agent:Compliance find_missing (1 gap)
   ...
   [every single operation]
   ```
4. Replays reasoning trace:
   ```
   Planner → DocAnalyzer → SecurityOfficer → Compliance → ...
   [every agent step with input/output/reasoning]
   ```
5. Can verify: no bias, all decisions legally grounded with Citations
6. Shares report with complainant + supervisor

### Value
- Before: impossible to fully reconstruct → escalates to witness testimony
- After: complete forensic trail in 5 minutes
- **Accountability + trust**

---

## Journey matrix — 5 personas × 5 TTHC

| Persona | CPXD | GCN QSDĐ | ĐKKD | LLTP | GPMT |
|---|---|---|---|---|---|
| **Citizen/Business** | Submit, track, upload missing, download | Same pattern | Same | Same | Same |
| **Front desk** | Scan, auto-fill, create | Same | Same | Same | Same |
| **Chuyên viên** | Compliance review, consult if needed | Same with Đất đai legal corpus | Quick (3-day SLA) | Simple process | Complex multi-reviewer |
| **Leadership** | Batch approve low-risk, review high-value | Same | Same | Same | Higher scrutiny |
| **Pháp chế** | Consult on edge cases | Consult on đất đai disputes | Rare consult | Rare | Often consulted |
| **Security** | Monitor, investigate, audit | Same | Same | Watch PII carefully | Watch environmental sensitive cases |

Each persona has same UX patterns across TTHCs — consistency reduces cognitive load.

## Key insights

1. **Citizen UX is the reputation critical path.** One bad citizen experience kills adoption.
2. **Chuyên viên save time is the value prop quantifiable.** 5-10× throughput justifies subscription.
3. **Leadership saves + gains visibility.** They're the decision maker for procurement.
4. **Pháp chế + Security are "deep value" personas.** Infrequent but high-impact usage.
5. **Consistency across TTHCs is a design goal.** Once learned, works everywhere.
