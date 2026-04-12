# Scope Decision — Why TTHC Công, not Văn Thư Nội Bộ

## The critical interpretation call

Khi đọc PDF lần đầu, có thể hiểu đề bài theo 2 cách:

**(A) Hẹp — "AI xử lý văn thư nội bộ":** số hoá luồng công văn, tờ trình, quyết định nội bộ giữa các phòng ban. Giải pháp dạng document management system + OCR + classification.

**(B) Rộng — "AI điều hành toàn bộ thủ tục hành chính công":** xử lý end-to-end vòng đời TTHC từ công dân/doanh nghiệp nộp hồ sơ đến nhận kết quả. Giải pháp là platform cho một-cửa-liên-thông thế hệ mới.

## We chose (B). Here's why.

### Evidence from PDF

1. **"Citizen Experience"** là 1 trong 3 Key Impact Areas → đề bài quan tâm **người dân**, không chỉ nội bộ
2. **"Slower response times to citizens and stakeholders"** → beneficiary là citizen
3. **"Administrative documents across public sector organizations"** → cross-org, không chỉ 1 phòng văn thư
4. **"Final responses issued to citizens/stakeholders"** (Step 6) → output cuối cùng đi về citizen
5. **"Restricted access based on user roles"** + multi-level classification → không chỉ công chức nội bộ, mà phân cấp truy cập phức tạp hơn — phù hợp với hệ thống TTHC công có nhiều loại stakeholder

### Evidence from Vietnamese regulatory landscape

6 bước trong PDF **chính xác** là khung của **cơ chế một cửa liên thông** trong NĐ 61/2018/NĐ-CP:
- Intake = Tiếp nhận hồ sơ tại bộ phận một cửa
- Registration = Vào sổ, cấp mã hồ sơ
- Distribution = Chuyển phòng chuyên môn
- Review = Thẩm định
- Consultation = Xin ý kiến liên ngành
- Response = Trả kết quả

Đây là ngôn ngữ chuẩn của luật TTHC công Việt Nam.

### Evidence from sponsor intent

**Shinhan InnoBoost** (200M VND PoC funding) nhắm vào startup giải quyết bài toán **kinh doanh có thể scale** cho khu vực công. "Document management nội bộ" có TAM nhỏ (chủ yếu IT budget các Sở). "Nền tảng TTHC công" có TAM khổng lồ (63 tỉnh × N Sở × hàng triệu công dân/năm).

Shinhan muốn thấy **pipeline thương mại rõ ràng** — scope (B) cho câu chuyện đó dễ hơn nhiều.

### Evidence from market reality

Ở Việt Nam:
- Các hệ thống "document management + OCR" đã có nhiều (FPT.IS, Viettel AI, VNPT, Misa AMIS...) → đề bài rẻ tiền nếu chọn scope (A)
- Nền tảng "AI cho TTHC công end-to-end" chưa ai làm hoàn chỉnh → blue ocean nếu chọn scope (B)

## Implications of choosing (B)

Mọi phần còn lại của docs được viết theo scope (B):

1. **Painpoint analysis** mở rộng từ "chuyên viên văn thư" → **6 nhóm stakeholder** (công dân/DN, cán bộ một cửa, chuyên viên phòng, lãnh đạo, pháp chế/thanh tra, CIO)
2. **5 TTHC flagship** để demo:
   - Cấp phép xây dựng
   - Cấp GCN quyền sử dụng đất
   - Đăng ký kinh doanh
   - Cấp lý lịch tư pháp
   - Giấy phép môi trường
3. **Compliance framework** bám trọn bộ NĐ 61/107/45/42/30 + Đề án 06 + Luật BVBMNN + ANM + BVDLCN
4. **Agent catalog** có những agent đặc thù TTHC công: `Compliance`, `LegalLookup`, `Consult`, `Drafter`, `Router` (org structure) — không chỉ có `Classifier` + `Summarizer` như scope hẹp
5. **UX** có **Citizen Portal** là mặt tiền — không chỉ internal dashboard
6. **Business case** kể chuyện 63 tỉnh × N Sở thay vì "chúng tôi bán DMS cho 1 văn phòng"

## Risk of the decision

Scope (B) khó hơn scope (A) về technical execution — bài toán to hơn → phải prioritize gắt gao. Mitigation: 5 TTHC flagship với full cross-reference (không 50 TTHC shallow), architecture graph-native giải quyết nhiều vấn đề cùng 1 pattern.

## Final word

**Scope (B) là moat.** Bất kỳ đội nào khác cũng có thể làm OCR + classification. Không nhiều đội dám reframe bài toán thành "operating system của bộ máy hành chính". Đây là điểm khác biệt lớn nhất ở tiêu chí **Problem Relevance**.
