# Stakeholder Personas — 6 nhân vật chính

Mỗi persona có 1 scenario cụ thể để dùng trong pitch + demo. Personas giúp cả team "nghĩ như user" khi build feature.

---

## Persona 1 — Anh Minh (Doanh nghiệp nhỏ)

- **Tuổi / nghề:** 38, chủ công ty xây dựng quy mô nhỏ ở Bình Dương
- **Context:** Muốn xin cấp phép xây dựng nhà xưởng 500m² để mở rộng sản xuất
- **Tech proficiency:** Dùng Zalo, Google Maps thành thạo; chưa quen với portal nhà nước
- **Goals:** Có giấy phép XD càng nhanh càng tốt để khởi công trước mùa mưa
- **Pain:**
  - Đã đi nộp hồ sơ 2 lần, lần nào cũng thiếu giấy mà không ai báo trước
  - Không biết hồ sơ đang ở phòng nào, gọi hotline không ai trả lời cụ thể
  - Luật quy định 15 ngày, đã 25 ngày mà vẫn im
- **Sử dụng GovFlow:** Citizen Portal — upload bundle qua mobile, track realtime, nhận notification khi thiếu giấy hoặc cần bổ sung
- **Success moment:** Upload hồ sơ lúc sáng → trưa nhận thông báo "thiếu văn bản thẩm duyệt PCCC" có link hướng dẫn → đi lấy chiều → nộp lại → hôm sau có giấy phép

---

## Persona 2 — Chị Lan (Cán bộ tiếp nhận tại Bộ phận Một cửa)

- **Tuổi / nghề:** 32, chuyên viên tiếp nhận tại Bộ phận Một cửa Sở Xây dựng Bình Dương
- **Context:** Tiếp 30–50 lượt công dân/ngày, mỗi lượt 10–20 phút check hồ sơ
- **Tech proficiency:** Dùng thành thạo Windows + phần mềm một cửa của tỉnh; chưa dùng AI
- **Goals:** Không để dân phải đi lại. Giảm sai sót check thiếu thành phần. Về đúng giờ.
- **Pain:**
  - Phải thuộc lòng danh mục thành phần của hàng chục TTHC, mà luật lại đổi
  - Phải đánh máy lại thông tin từ CCCD, sổ đỏ, giấy phép KD vào hệ thống
  - Gặp hồ sơ giáp ranh lĩnh vực thì phải hỏi lãnh đạo
- **Sử dụng GovFlow:** Intake UI — scan bundle, xem auto-fill từ DocAnalyzer, nhận gợi ý loại TTHC từ Classifier, nhận checklist Compliance realtime
- **Success moment:** Scan hồ sơ → trong 30 giây thấy "Thiếu giấy phép môi trường" → báo công dân ngay, không phải đợi đến hôm sau

---

## Persona 3 — Anh Tuấn (Chuyên viên phòng Quản lý Xây dựng)

- **Tuổi / nghề:** 45, chuyên viên chính Phòng QLXD Sở XD Bình Dương, 15 năm kinh nghiệm
- **Context:** Đang ôm 35 hồ sơ active. Mỗi ngày xử lý 3–5 hồ sơ mới.
- **Tech proficiency:** Dùng Word, Excel, email. Chưa quen với AI.
- **Goals:** Không sai luật. Không bị kỷ luật. Về đúng giờ (6h chiều).
- **Pain:**
  - Mỗi hồ sơ phải đối chiếu Luật XD 2014, NĐ 15/2021, TT 15/2016, QĐ địa phương, NĐ 136/2020 PCCC → tốn 1–2h tra cứu
  - Cần ý kiến phòng Pháp chế, Quy hoạch → gửi công văn → đợi 3–7 ngày
  - Soạn tờ trình cho lãnh đạo → copy-paste từ mẫu cũ → dễ sót
- **Sử dụng GovFlow:** Compliance Workspace — thấy checklist tự động, legal panel có trích dẫn điều luật cụ thể, consult auto-triggered
- **Success moment:** Mở hồ sơ → thấy ngay "Compliance 94%, thiếu thông tin PCCC" + nút "Xin ý kiến Pháp chế" 1-click → hoàn thành tờ trình trong 30 phút thay vì 3 giờ

---

## Persona 4 — Chị Hương (Phó Giám đốc Sở XD)

- **Tuổi / nghề:** 48, Phó GĐ Sở XD phụ trách cấp phép, 20 năm ngành
- **Context:** Ký 30–60 quyết định/ngày. Đồng thời điều hành 3 phòng.
- **Tech proficiency:** Dùng iPad, email, ký số đã quen
- **Goals:** SLA compliance cao để báo cáo UBND tỉnh. Không có khiếu nại. Không sai luật.
- **Pain:**
  - Phải ký mù hoặc đọc tờ trình dài; không có TL;DR + compliance score
  - Không biết phòng nào đang bottleneck đến khi có khiếu nại
  - Bị thanh tra soi SLA mà không có dữ liệu reports-ready
- **Sử dụng GovFlow:** Leadership Dashboard — SLA heatmap per TTHC, danh sách cần ký với TL;DR + compliance score, alerts overdue, export báo cáo NĐ 61 1-click
- **Success moment:** Mở dashboard buổi sáng → thấy 3 hồ sơ sắp overdue trong tuần, 1 click escalate → chiều ký bundle 15 hồ sơ với TL;DR + compliance score, mỗi cái 30 giây thay vì 5 phút

---

## Persona 5 — Anh Dũng (Chuyên viên Phòng Pháp chế)

- **Tuổi / nghề:** 40, chuyên viên phòng Pháp chế của UBND tỉnh, phụ trách tư vấn pháp lý cross-sector
- **Context:** Nhận 15–25 yêu cầu xin ý kiến/ngày từ các Sở
- **Tech proficiency:** Dùng thuvienphapluat.vn hàng ngày, Word
- **Goals:** Ý kiến đúng, kịp hạn, có căn cứ rõ ràng
- **Pain:**
  - Mỗi yêu cầu không có context đủ, phải tự đọc lại cả hồ sơ
  - Phải tự mở VB pháp luật search keyword — không có công cụ contextual
  - Không biết cùng vấn đề trước đây đã tư vấn thế nào
- **Sử dụng GovFlow:** Consult Inbox — nhận yêu cầu đã pre-summarize + LegalLookup pre-run, trả lời với 1 click "sử dụng trích dẫn này"
- **Success moment:** Nhận 15 yêu cầu/ngày → xử lý được hết trong 3 giờ thay vì cả ngày

---

## Persona 6 — Anh Quốc (Chánh Văn phòng Sở / IT Security)

- **Tuổi / nghề:** 50, Chánh văn phòng kiêm phụ trách CĐS tại Sở XD
- **Context:** Phải tuân thủ Luật ANM, Luật BVBMNN, NĐ 53/2022, Đề án 06
- **Tech proficiency:** Cao — từng làm IT trước khi chuyển gov
- **Goals:** Không rò rỉ dữ liệu mật. Audit trail đầy đủ. Tuân thủ báo cáo thanh tra.
- **Pain:**
  - Không dám dùng ChatGPT vì data residency
  - VB mật hiện tại vẫn dùng tủ sắt + phong bì → không enforcement số hoá
  - Hệ thống log yếu, không forensic được
- **Sử dụng GovFlow:** Security Console — ABAC policy editor, audit forensic timeline, replay access events, anomaly detection
- **Success moment:** Nhận thông báo "có 5 access bất thường từ user X lúc 2h sáng" → 1 click replay agent trail → thấy đầy đủ context → disable user trong 10 giây

---

## Tại sao personas quan trọng

1. **Designers** — dùng để quyết định feature nào ưu tiên
2. **Pitch** — kể câu chuyện anh Minh (Persona 1) sẽ resonate hơn là "giảm SLA 70%"
3. **Demo video** — 8 scene trong demo theo đúng anh Minh + chị Lan + anh Tuấn + chị Hương + anh Quốc
4. **QA prep** — judge hỏi "ai là người dùng?" → có câu trả lời concrete với 6 personas

## Multi-persona journey cho 1 case CPXD

Từ lúc anh Minh nộp hồ sơ đến lúc anh Minh cầm giấy phép:

```
Anh Minh (1) ──upload── Chị Lan (2) ──route──> Anh Tuấn (3) ──consult──> Anh Dũng (5)
                                                     │
                                                     ▼
                                               Chị Hương (4) ──approve──> Drafter ──> Anh Minh (1)
                                                     ▲
                                                     │
                                         Anh Quốc (6) monitors all access
```

5/6 personas tương tác trực tiếp với hệ thống. Persona 6 (security) monitors và enforce quyền truy cập cho toàn bộ chain.
