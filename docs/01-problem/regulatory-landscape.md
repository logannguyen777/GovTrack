# Regulatory Landscape — Khung pháp lý TTHC công Việt Nam

Đây là bộ văn bản pháp luật mà GovFlow phải tuân thủ và *tận dụng làm tiếng nói pitch*. Judge sẽ ấn tượng khi thấy team hiểu sâu regulatory framework.

## Tier 1 — Khung chính cho TTHC công

### Nghị định 61/2018/NĐ-CP — Cơ chế một cửa, một cửa liên thông
- **Ban hành:** 23/04/2018
- **Nội dung:** Quy định cơ chế một cửa, một cửa liên thông trong giải quyết TTHC
- **Quan trọng:** Quy định chính thức **6 bước workflow** mà PDF đề bài mô tả (Tiếp nhận → Vào sổ → Chuyển → Thẩm định → Xin ý kiến → Trả kết quả). **Đây là foundation pháp lý của scope (B).**
- **GovFlow impact:** Toàn bộ pipeline + state machine được thiết kế khớp NĐ 61.
- **Pitch quote:** *"GovFlow automate đúng 6 bước trong NĐ 61/2018 về cơ chế một cửa liên thông."*

### Nghị định 107/2021/NĐ-CP — Sửa đổi NĐ 61/2018
- **Ban hành:** 06/12/2021
- **Nội dung:** Cập nhật cơ chế một cửa điện tử, yêu cầu interoperability giữa các hệ thống
- **Quan trọng:** Push mạnh việc số hoá một cửa, yêu cầu các tỉnh có hệ thống phần mềm
- **GovFlow impact:** Architecture có OpenAPI spec để tích hợp với hệ thống một cửa hiện có của tỉnh

### Nghị định 45/2020/NĐ-CP — Thực hiện TTHC trên môi trường điện tử
- **Ban hành:** 08/04/2020
- **Nội dung:** Giá trị pháp lý của hồ sơ điện tử, chữ ký số của công dân/tổ chức, thanh toán điện tử
- **Quan trọng:** Đây là cơ sở pháp lý cho phép mình xử lý hồ sơ *thuần điện tử* (không cần giấy)
- **GovFlow impact:** Citizen Portal dùng VNeID + chữ ký số theo NĐ 45

### Nghị định 42/2022/NĐ-CP — Cung cấp thông tin và dịch vụ công trực tuyến
- **Ban hành:** 24/06/2022
- **Nội dung:** Chuẩn dịch vụ công trực tuyến 4 mức độ (1: thông tin → 2: tương tác → 3: nộp hồ sơ → 4: hoàn tất online)
- **GovFlow impact:** Target làm dịch vụ mức độ 4 cho các TTHC flagship

### Nghị định 30/2020/NĐ-CP — Công tác văn thư
- **Ban hành:** 05/03/2020
- **Nội dung:** Thể thức VB hành chính, số hiệu, lưu trữ, ký số. Lần đầu quy định giá trị pháp lý của VB điện tử.
- **GovFlow impact:** `Drafter` agent sinh VB output **đúng thể thức NĐ 30** (quốc hiệu, tiêu ngữ, số/ký hiệu, căn cứ, trích yếu, nội dung, nơi nhận, người ký).

### Quyết định 06/QĐ-TTg ngày 06/01/2022 — Đề án 06
- **Ban hành:** 06/01/2022
- **Nội dung:** Phát triển ứng dụng dữ liệu về dân cư, định danh và xác thực điện tử (VNeID) phục vụ CĐS quốc gia 2022–2025 tầm nhìn 2030
- **Quan trọng:** Nền tảng cho việc integrate VNeID vào mọi TTHC
- **GovFlow impact:** Citizen Portal authenticate qua VNeID; verify identity theo Đề án 06

## Tier 2 — Bảo mật và dữ liệu

### Luật Bảo vệ bí mật nhà nước 2018
- **Ban hành:** 15/11/2018
- **Nội dung:** 4 cấp độ mật (Tuyệt mật / Tối mật / Mật / và Unclassified). Quy trình xác định, xử lý, lưu trữ, tiêu huỷ.
- **Quan trọng:** Bắt buộc GovFlow enforce multi-level classification
- **GovFlow impact:** `SecurityOfficer` agent + 3-tier Permission Engine + 4 classification level UI

### Luật An ninh mạng 2018
- **Ban hành:** 12/06/2018
- **Nội dung:** Yêu cầu dữ liệu công dân Việt Nam phải lưu trữ tại Việt Nam
- **GovFlow impact:** Kiến trúc có on-prem deployment option; LLM dùng Qwen open-weight có thể chạy on-prem

### Nghị định 53/2022/NĐ-CP — Hướng dẫn Luật ANM
- **Ban hành:** 15/08/2022
- **Nội dung:** Chi tiết về lưu trữ dữ liệu trong nước, các loại dữ liệu bắt buộc lưu trữ, thời hạn
- **GovFlow impact:** Backend chạy tại Alibaba Cloud VN/Singapore region; roadmap on-prem cho tỉnh yêu cầu

### Luật Bảo vệ dữ liệu cá nhân 2023
- **Ban hành:** Dự kiến có hiệu lực đầy đủ 2024 (theo lịch sửa đổi)
- **Nội dung:** Quy định về thu thập, xử lý, lưu trữ, chia sẻ dữ liệu cá nhân công dân
- **GovFlow impact:** Property mask middleware cho PII; purpose limitation per agent; audit trail

### Nghị định 13/2023/NĐ-CP — Bảo vệ dữ liệu cá nhân
- **Ban hành:** 17/04/2023
- **Nội dung:** Hướng dẫn cụ thể cho việc xử lý dữ liệu cá nhân, yêu cầu DPIA, consent management
- **GovFlow impact:** Agent profile có `purpose_limitation`; data minimization qua property mask

## Tier 3 — Luật chuyên ngành cho 5 TTHC flagship

### Cấp phép xây dựng
- **Luật Xây dựng 2014** (sửa đổi 2020) — Điều 89–102
- **Nghị định 15/2021/NĐ-CP** — hướng dẫn chi tiết cấp phép XD, thẩm định thiết kế
- **Nghị định 136/2020/NĐ-CP** — PCCC (yêu cầu thẩm duyệt cho công trình nhóm đặc biệt)
- **Luật Quy hoạch đô thị 2009** + các QĐ quy hoạch địa phương

### Cấp GCN quyền sử dụng đất
- **Luật Đất đai 2024** (có hiệu lực 01/08/2024)
- **Nghị định 101/2024/NĐ-CP** — hướng dẫn Luật Đất đai mới
- **Thông tư 10/2024/TT-BTNMT** — chi tiết thủ tục

### Đăng ký kinh doanh
- **Luật Doanh nghiệp 2020**
- **Nghị định 01/2021/NĐ-CP** — đăng ký doanh nghiệp
- **Thông tư 01/2021/TT-BKHĐT** — biểu mẫu

### Cấp lý lịch tư pháp
- **Luật Lý lịch tư pháp 2009**
- **Nghị định 111/2010/NĐ-CP** — hướng dẫn thi hành
- **Thông tư liên tịch 04/2012/TTLT-BTP-BCA** — hồ sơ cấp LLTP

### Giấy phép môi trường
- **Luật Bảo vệ môi trường 2020**
- **Nghị định 08/2022/NĐ-CP** — hướng dẫn Luật BVMT mới
- **Thông tư 02/2022/TT-BTNMT** — biểu mẫu và quy trình

## Compliance principles GovFlow tuân thủ

1. **Legal traceability** — mọi quyết định phải có `CITES` edge về Article node trong KG → có thể point-and-click từ quyết định về điều luật gốc
2. **Data minimization** — agent chỉ truy cập field cần thiết (property mask)
3. **Purpose limitation** — mỗi agent có scope rõ ràng, không được dùng data ngoài purpose
4. **Audit trail immutable** — mọi access/write sinh AuditEvent không xoá được
5. **Multi-level security** — 4 classification level enforce xuyên suốt pipeline
6. **Data residency** — option on-prem cho data sensitive
7. **Consent + transparency** — citizen biết hồ sơ của mình đang ở đâu, ai xử lý (purpose-limited)

## Dùng trong pitch

Judge sẽ ấn tượng khi nghe:
> "GovFlow được thiết kế tuân thủ 9 văn bản pháp luật cốt lõi của Việt Nam: NĐ 61/2018 + 107/2021 cho cơ chế một cửa, NĐ 45/2020 + 42/2022 cho TTHC điện tử, NĐ 30/2020 cho thể thức văn bản, Đề án 06 cho VNeID, Luật BVBMNN 2018 cho multi-level classification, Luật ANM + NĐ 53/2022 cho data residency, và Luật BVDLCN + NĐ 13/2023 cho xử lý dữ liệu cá nhân. Mỗi feature đều có legal anchor cụ thể."

Đây là tone mà đội khác khó ganh — vì cần **hiểu sâu hệ thống pháp luật Việt Nam**.
