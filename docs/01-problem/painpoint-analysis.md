# Painpoint Analysis — 6 nhóm stakeholder TTHC Việt Nam

PDF đề bài nêu 3 challenge ở mức bullet. Để pitch thuyết phục và thiết kế giải pháp đúng chỗ đau, cần đào sâu cái đau thật của từng nhóm stakeholder.

## Scope context

Đây là painpoint của **toàn bộ thủ tục hành chính công (TTHC)** ở Việt Nam — không chỉ văn thư nội bộ. Xem [`../00-context/scope-decision.md`](../00-context/scope-decision.md).

---

## Nhóm 1 — Người dân / Doanh nghiệp (end beneficiary)

Chính là "Citizen Experience" mà PDF trang 1 nói tới. Đây là nhóm bị đau nhiều nhất nhưng thường bị bỏ quên khi thiết kế giải pháp gov-tech.

### 1.1. "Đi lại nhiều lần"

**Biểu hiện:** Nộp thiếu giấy → về lấy → nộp lại → lại thiếu → tổng 3–5 chuyến đi cho 1 hồ sơ.

**Nguyên nhân gốc:** Không có công cụ pre-check tại nguồn. Cán bộ tiếp nhận phải thuộc lòng danh mục thành phần của hàng trăm loại TTHC để check — sai sót không tránh khỏi. Thông tin "còn thiếu gì" thường được thông báo sau 3–7 ngày.

**Hậu quả:** Chi phí xã hội khổng lồ (thời gian, đi lại, xin nghỉ làm). Mất niềm tin vào dịch vụ công.

### 1.2. "Không biết hồ sơ của mình đang ở đâu, ai đang giữ"

**Biểu hiện:** Gọi tổng đài chỉ biết "đang xử lý". Trên Cổng DVC chỉ thấy status chung chung (Tiếp nhận / Đang xử lý / Đã trả kết quả). Không biết đang kẹt ở phòng nào, ai ôm, bao giờ xong.

**Nguyên nhân gốc:** Hệ thống backend không có single source of truth. Mỗi phòng có state của riêng họ, không stream lên portal.

**Hậu quả:** Lo lắng. Phải có quan hệ hoặc phải "biếu" mới hỏi được tình hình thật. Mất niềm tin.

### 1.3. "Ngâm hồ sơ" / overdue SLA

**Biểu hiện:** Luật quy định cấp phép XD 15 ngày → thực tế 1–3 tháng là bình thường. Đăng ký kinh doanh 3 ngày → thực tế 5–10 ngày. Cấp lý lịch tư pháp 10 ngày → thực tế có khi 20 ngày.

**Nguyên nhân gốc:** Chuyên viên quá tải; không có SLA clock tự động + escalation; lãnh đạo không thấy bức tranh tổng để prioritize.

**Hậu quả:** Doanh nghiệp delay project, chi phí cơ hội lớn. Chỉ số PCI (năng lực cạnh tranh cấp tỉnh) của VN luôn xếp "TTHC" là top-3 điểm đau.

### 1.4. Không hiểu vì sao bị từ chối

**Biểu hiện:** Văn bản từ chối dùng ngôn ngữ pháp lý khô khan, chỉ trích dẫn điều luật mà không giải thích sai ở đâu, sửa thế nào.

**Nguyên nhân gốc:** Chuyên viên copy-paste template, không có thời gian giải thích.

**Hậu quả:** Công dân nộp lại vẫn sai → vòng lặp vô tận. Tăng gánh nặng cho chính cơ quan.

### 1.5. Không biết quy định nào đang áp dụng

**Biểu hiện:** 1 TTHC có thể được điều chỉnh bởi Luật + NĐ hướng dẫn + Thông tư + QĐ địa phương + văn bản cập nhật. Công dân không có cách tra cứu đơn giản.

**Nguyên nhân gốc:** Hệ thống pháp luật phức tạp, không có công cụ tra cứu contextual.

**Hậu quả:** Nộp sai, bị "vận dụng" khi pháp luật mơ hồ.

---

## Nhóm 2 — Cán bộ tiếp nhận (Bộ phận Một cửa)

Đây là "front desk" — nơi đầu tiên tiếp xúc với công dân. Khối lượng công việc cao, dễ sai sót.

### 2.1. Phải thuộc lòng hàng trăm bộ thủ tục để check hồ sơ đủ thành phần

**Biểu hiện:** Mỗi TTHC có danh mục giấy tờ riêng. Luật thay đổi liên tục (mỗi năm có cả trăm văn bản mới). Không có tool hỗ trợ.

**Hậu quả:** Check sai → trả nhầm → dân khiếu nại → cán bộ bị kỷ luật. Stress.

### 2.2. Nhập liệu thủ công vào hệ thống một cửa

**Biểu hiện:** Công dân mang CMND/CCCD, sổ đỏ, giấy phép kinh doanh → cán bộ đánh máy lại hết vào hệ thống. Cùng 1 thông tin nhập 3–5 lần trong 1 hồ sơ.

**Hậu quả:** Sai sót nhập liệu, chậm, mệt.

### 2.3. Phải phân loại thủ công hồ sơ thuộc nhóm/phòng nào

**Biểu hiện:** Giáp ranh nhiều lĩnh vực (đất đai vs xây dựng vs môi trường vs quy hoạch) → phải hỏi lãnh đạo quyết định.

**Hậu quả:** Backlog ngay tại intake.

---

## Nhóm 3 — Chuyên viên phòng chuyên môn

Đây là người *thực sự xử lý* hồ sơ. Painpoint nhiều nhất về mặt tác nghiệp.

### 3.1. Quá tải — mỗi người ôm 20–50 hồ sơ active

**Biểu hiện:** Không thể đọc kỹ từng cái. Không có TL;DR. Phải skim → dễ sót → quyết định chậm hoặc rập khuôn.

### 3.2. Phải đọc chéo hồ sơ với luật/nghị định/thông tư liên quan

**Biểu hiện:** 1 hồ sơ cấp phép XD phải đối chiếu Luật XD 2014, NĐ 15/2021, TT hướng dẫn, QĐ địa phương về quy hoạch, NĐ 136/2020 về PCCC... Mỗi lần là hàng giờ tra cứu.

**Nguyên nhân gốc:** Không có công cụ contextual legal lookup. Phải Ctrl+F trong PDF.

**Hậu quả:** 30–50% thời gian chuyên viên dành cho tra cứu, không phải thẩm định.

### 3.3. Consult chéo phòng khác thủ công

**Biểu hiện:** Cần ý kiến pháp chế, tài chính, chuyên ngành khác → gửi công văn xin ý kiến → chờ 3–7 ngày → tổng hợp thủ công vào tờ trình.

**Hậu quả:** Extended approval cycles (đúng như PDF nêu).

### 3.4. Soạn thảo VB trả lời / quyết định thủ công

**Biểu hiện:** Copy-paste từ mẫu cũ. Dễ sót, sai tên, sai số hiệu.

**Hậu quả:** Sản phẩm đầu ra chất lượng không đều.

### 3.5. Sợ ký — sợ sai luật → xin ý kiến lên trên cho chắc

**Biểu hiện:** Thiếu tool kiểm tra tuân thủ → mỗi quyết định đều muốn xin ý kiến sếp → sếp quá tải.

**Hậu quả:** Tầng lớp duyệt bị phình, everyone overloaded.

---

## Nhóm 4 — Lãnh đạo phòng / Sở / Bộ

### 4.1. Không có bức tranh tổng thời gian thực

**Biểu hiện:** Không biết có bao nhiêu hồ sơ đang chờ, bao nhiêu quá hạn, bottleneck ở đâu. Chỉ biết qua báo cáo định kỳ.

**Hậu quả:** Không prioritize được, bị động.

### 4.2. Phải ký tay / ký số rất nhiều mà không có TL;DR + compliance check

**Biểu hiện:** Ký mù 20–50 VB/ngày. Hoặc bắt chuyên viên làm tờ trình đầy đủ rồi vẫn ký mù.

**Hậu quả:** Rủi ro cá nhân cao.

### 4.3. Không đo được hiệu suất cán bộ dưới quyền

**Biểu hiện:** Không biết ai làm nhanh, ai ngâm, ai thường xử lý sai.

**Hậu quả:** KPI không công bằng, khó cải thiện.

### 4.4. Bị cấp trên và thanh tra soi SLA mà không có dữ liệu

**Biểu hiện:** NĐ 61/2018 quy định SLA cụ thể cho từng TTHC. Khi vi phạm, bị nhắc nhưng không có data để phản biện hoặc explain.

**Hậu quả:** Áp lực chính trị lớn.

---

## Nhóm 5 — Phòng Pháp chế / Thanh tra / Kiểm toán nội bộ

### 5.1. Bị consult ngập đầu, không có tool support

**Biểu hiện:** Mỗi ngày nhận 10–30 yêu cầu xin ý kiến từ các phòng khác. Phải tự đọc, tự tra luật, tự viết ý kiến.

**Hậu quả:** Trả chậm → kéo timeline TTHC.

### 5.2. Không có công cụ tra cứu luật xuyên suốt + theo ngữ cảnh

**Biểu hiện:** Phải tự mở văn bản pháp luật search keyword. Không biết điều nào đã bị sửa, điều nào đã bị thay thế.

**Hậu quả:** Tốn thời gian, dễ miss quy định mới.

### 5.3. Không audit được toàn bộ lifecycle hồ sơ sau sự việc

**Biểu hiện:** Khi có khiếu nại → không reconstruct được "ai quyết định gì lúc nào".

**Hậu quả:** Không xử lý được trách nhiệm.

---

## Nhóm 6 — CIO / IT Security / Ban chỉ đạo CĐS

### 6.1. Không thể dùng ChatGPT/Gemini cho dữ liệu công dân

**Biểu hiện:** Luật ANM 2018 + NĐ 53/2022: dữ liệu phải lưu tại VN. Dữ liệu cá nhân + mật nhà nước không được rời hạ tầng kiểm soát.

**Hậu quả:** Mất cơ hội dùng LLM thế hệ mới. Chờ đợi giải pháp on-prem.

### 6.2. Hệ thống phân mảnh (PDF gọi "Fragmented Systems")

**Biểu hiện:** Cổng DVC Quốc gia + hệ thống một cửa tỉnh + phần mềm chuyên ngành + Excel + giấy — không nói chuyện với nhau.

**Hậu quả:** Không có single source of truth.

### 6.3. Multi-level classification cưỡng chế thủ công

**Biểu hiện:** VB mật được bảo vệ bằng tủ sắt + phong bì dán. Không có enforcement số hoá.

**Hậu quả:** Rủi ro rò rỉ lớn. Vi phạm Luật BVBMNN 2018.

### 6.4. Audit trail yếu

**Biểu hiện:** Hệ thống hiện tại log thiếu chi tiết. Không forensic được — không biết ai access, khi nào, từ đâu, tải về hay view.

**Hậu quả:** Không phát hiện được insider threat, không điều tra được sự cố.

---

## Painpoint summary

**25 painpoint cụ thể × 6 nhóm stakeholder.** Mỗi painpoint sẽ được map sang 1 feature/agent trong [`../02-solution/coverage-matrix.md`](../02-solution/coverage-matrix.md).

**Cái đau tổng thể:** Việt Nam đang push mạnh chuyển đổi số TTHC công qua Đề án 06, Cổng DVC Quốc gia, nhưng **backend vẫn chạy thủ công**. GovFlow giải quyết chính cái gap này — "agent layer" thông minh chạy phía sau các Cổng DVC hiện có, biến quy trình 6 bước từ manual thành tự động hoá end-to-end với human-in-the-loop đúng chỗ.
