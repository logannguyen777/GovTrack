# Legal Framework Mapping — Feature ↔ Điều luật cụ thể

Mỗi feature của GovFlow được map đến 1 hoặc nhiều điều luật cụ thể. Đây là bằng chứng compliance + là tiếng nói thuyết phục cho pitch.

## Full mapping table

| GovFlow Feature | Legal Anchor | Điều cụ thể |
|---|---|---|
| **6-step workflow** (Intake → Response) | NĐ 61/2018/NĐ-CP | Điều 6, 7, 8 (quy trình giải quyết TTHC một cửa) |
| **One-stop integration** | NĐ 107/2021/NĐ-CP | Điều 1 (sửa đổi NĐ 61) — một cửa điện tử |
| **Digital TTHC submission** | NĐ 45/2020/NĐ-CP | Điều 3, 4 (giá trị pháp lý hồ sơ điện tử) |
| **Citizen Portal 4-level service** | NĐ 42/2022/NĐ-CP | Điều 5 (cấp độ dịch vụ công trực tuyến) |
| **Drafter thể thức VB** | NĐ 30/2020/NĐ-CP | Điều 8 (thể thức văn bản hành chính) + Phụ lục |
| **Digital signature on output** | NĐ 130/2018/NĐ-CP | Luật Giao dịch điện tử 2005 (hiệu lực) |
| **VNeID citizen authentication** | QĐ 06/QĐ-TTg/2022 | Đề án 06 — định danh điện tử |
| **SecurityOfficer 4-level classification** | Luật BVBMNN 2018 | Điều 3, 11, 12, 13 (4 cấp độ mật + quy trình) |
| **Audit trail immutable** | Luật BVBMNN 2018 | Điều 18 (bảo quản tài liệu mật) + NĐ 26/2020 |
| **On-prem data residency option** | Luật ANM 2018 | Điều 26 (dữ liệu phải lưu trong nước) |
| **Data residency enforcement** | NĐ 53/2022/NĐ-CP | Điều 26 (các loại dữ liệu bắt buộc) |
| **Property mask for PII** | Luật BVDLCN 2023 | Điều 4, 5 (nguyên tắc xử lý dữ liệu cá nhân) |
| **Consent management** | NĐ 13/2023/NĐ-CP | Điều 11–15 (consent, purpose limitation) |
| **Case lifecycle retention** | NĐ 30/2020/NĐ-CP | Điều 28 (thời hạn lưu trữ) + Luật Lưu trữ 2011 |
| **SLA per TTHC enforcement** | NĐ 61/2018/NĐ-CP | Điều 12 (thời hạn giải quyết) |
| **Compliance check CPXD** | Luật XD 2014 | Điều 89–102 (điều kiện cấp phép) |
| **Compliance check CPXD details** | NĐ 15/2021/NĐ-CP | Điều 41 (thành phần hồ sơ) |
| **PCCC check** | NĐ 136/2020/NĐ-CP | Điều 13, 15 (công trình phải thẩm duyệt) |
| **Compliance check GCN QSDĐ** | Luật Đất đai 2024 | Điều 149 (cấp GCN quyền sử dụng đất) |
| **Compliance check ĐKKD** | Luật DN 2020 | Điều 27, 28 (đăng ký thành lập DN) |
| **Compliance check LLTP** | Luật LLTP 2009 | Điều 46 (cấp phiếu LLTP) |
| **Compliance check GPMT** | Luật BVMT 2020 | Điều 43 (giấy phép môi trường) |
| **DSR endpoints (NĐ 13/2023)** | NĐ 13/2023/NĐ-CP | Điều 9 (quyền truy cập), Điều 10 (quyền xóa), Điều 11 (hạn chế mục đích) — `/api/dsr/export`, `/api/dsr/erasure` |
| **NĐ 30/2020 retention cron** | NĐ 30/2020/NĐ-CP | Điều 28 (thời hạn lưu trữ văn bản) — cron job tự động archive hồ sơ quá hạn |
| **Drafter chữ ký số validation** | NĐ 30/2020/NĐ-CP | Điều 25 + Điều 8 khoản 8 (chữ ký và dấu) — `validate_nd30_format()` kiểm tra placeholder chữ ký số trong mọi draft |

## Deep dive — key anchors

### NĐ 61/2018/NĐ-CP — Một cửa liên thông

**Why it matters:** Đây là backbone pháp lý cho scope của GovFlow. 6 bước trong PDF đề bài là **exact match** với 6 bước trong NĐ 61 Điều 6–8.

**Mapping:**
```
PDF Step          NĐ 61 Provision                Agent/Feature
────────────────────────────────────────────────────────────────
Intake            Điều 6.1 "Tiếp nhận hồ sơ"    Citizen Portal, Intake UI, DocAnalyzer
Registration      Điều 6.2 "Vào sổ"             Classifier, Case vertex creation
Distribution      Điều 6.3 "Chuyển hồ sơ"        Router
Review            Điều 7   "Xem xét, thẩm định" Compliance, LegalLookup
Consultation      Điều 7   "Xin ý kiến"          Consult
Response          Điều 8   "Trả kết quả"         Drafter, PublishedDoc
```

**SLA Điều 12:** GovFlow enforces SLA per TTHC với automatic escalation khi gần deadline.

### NĐ 30/2020/NĐ-CP — Công tác văn thư

**Why it matters:** Quy định thể thức văn bản hành chính. Drafter agent phải tuân thủ 100%.

**Key provisions affecting Drafter:**
- **Điều 8** — Thể thức VB hành chính gồm 9 thành phần bắt buộc:
  1. Quốc hiệu và tiêu ngữ
  2. Tên cơ quan, tổ chức ban hành
  3. Số, ký hiệu
  4. Địa danh, ngày, tháng, năm
  5. Tên loại và trích yếu nội dung
  6. Nội dung văn bản
  7. Chức vụ, họ tên và chữ ký người có thẩm quyền
  8. Dấu, chữ ký số
  9. Nơi nhận

- **Phụ lục I** — Mẫu trình bày VB cụ thể cho từng loại (Quyết định, Công văn, Thông báo, Giấy phép...)

- **Điều 25** — Giá trị pháp lý VB điện tử

**Drafter implementation:**
- Templates stored in KG per TTHC + doc_type
- Drafter output validated against all 9 thành phần
- Font: Times New Roman 13 (theo phụ lục)
- Chữ ký số per NĐ 130/2018 + Luật GDĐT

### Luật Bảo vệ bí mật nhà nước 2018

**Why it matters:** Đây là luật bắt buộc cho multi-level classification (Unclassified → Top Secret).

**4 classification levels (Điều 8):**
- **Tuyệt mật** (Top Secret) — gây tổn hại đặc biệt nghiêm trọng
- **Tối mật** (Secret) — gây tổn hại nghiêm trọng
- **Mật** (Confidential) — gây tổn hại
- **Unclassified** — default

**Enforcement Điều 11, 12, 13:**
- Quy trình xác định độ mật — SecurityOfficer agent implements
- Quy trình bảo quản — 3-tier Permission Engine
- Quy trình xử lý — Property Mask + access control

**Audit Điều 18:**
- Ghi nhật ký xử lý tài liệu mật — GovFlow AuditEvent

### Luật An ninh mạng 2018 + NĐ 53/2022

**Why it matters:** Data residency requirement cho dữ liệu công dân Việt Nam.

**Key provision (NĐ 53 Điều 26):**
- Dữ liệu cá nhân công dân VN phải lưu trữ tại Việt Nam
- Dữ liệu do người dùng Việt Nam tạo ra
- Dữ liệu về mối quan hệ của người dùng Việt Nam

**GovFlow response:**
- Primary deployment: Alibaba Cloud Singapore (lowest latency to VN)
- Production path: Alibaba Cloud on-prem deploy hoặc **Qwen3 open-weight via PAI-EAS** on customer hardware in VN
- Pitch talking point: *"Qwen open-weight + on-prem = giải pháp duy nhất dùng được LLM hàng đầu mà tuân thủ Điều 26 NĐ 53/2022"*

### Luật Bảo vệ dữ liệu cá nhân 2023 + NĐ 13/2023

**Why it matters:** Handling PII (CCCD, địa chỉ, phone, national ID) là core của TTHC.

**Key principles (Điều 4 Luật + Điều 11 NĐ 13):**
1. **Legality** — có căn cứ pháp lý rõ ràng
2. **Purpose limitation** — chỉ dùng cho mục đích cụ thể
3. **Data minimization** — chỉ thu thập data cần thiết
4. **Accuracy** — data phải chính xác
5. **Storage limitation** — không lưu quá lâu
6. **Security** — bảo mật
7. **Transparency** — công dân biết data được dùng thế nào

**GovFlow implementation:**
- Purpose limitation per agent: Compliance chỉ đọc data cần cho compliance check
- Data minimization via property mask: most agents không thấy national_id raw
- Storage limitation: retention policies per data type
- Security: 3-tier permission
- Transparency: Citizen Portal cho công dân xem ai đã access hồ sơ của họ

## Compliance self-audit checklist

Before pitch, verify GovFlow is compliant với:

- [ ] **NĐ 61/2018** — 6 bước workflow match + SLA enforcement
- [ ] **NĐ 107/2021** — API tương thích Cổng DVC
- [ ] **NĐ 45/2020** — hồ sơ điện tử có giá trị pháp lý
- [ ] **NĐ 42/2022** — dịch vụ công trực tuyến mức độ 4
- [ ] **NĐ 30/2020** — Drafter output đúng thể thức + 9 thành phần
- [ ] **QĐ 06/2022 (Đề án 06)** — VNeID integration hook
- [ ] **Luật BVBMNN 2018** — 4 level classification enforce
- [ ] **Luật ANM 2018 + NĐ 53/2022** — on-prem option ready
- [ ] **Luật BVDLCN 2023 + NĐ 13/2023** — data minimization + purpose limitation
- [ ] **Luật Lưu trữ 2011** — retention policies đúng

## Why this matters for pitch

When judges ask *"Has your team thought about compliance?"* — the answer is a 15-second recitation of the 9 laws above, each mapped to a specific feature. This is extremely rare in hackathons. It demonstrates:

1. **Domain expertise** — team hiểu luật VN
2. **Production readiness** — không phải "PoC tech demo" mà là "giải pháp có thể deploy thật"
3. **Risk mitigation** — không có surprise legal issues later

**Pitch quote:**
> *"GovFlow được thiết kế tuân thủ 9 văn bản pháp luật cốt lõi: NĐ 61/2018 + 107/2021 cho cơ chế một cửa, NĐ 45/2020 + 42/2022 cho TTHC điện tử, NĐ 30/2020 cho thể thức văn bản, Đề án 06 cho VNeID, Luật BVBMNN 2018 cho 4-level classification, Luật ANM + NĐ 53/2022 cho data residency, và Luật BVDLCN + NĐ 13/2023 cho xử lý dữ liệu cá nhân. Mỗi feature của chúng em đều có legal anchor cụ thể — không phải 'compliance by accident' mà là 'compliance by design'."*

## References

- Văn bản gốc: https://vanban.chinhphu.vn, https://thuvienphapluat.vn
- Cổng DVC Quốc gia: https://dichvucong.gov.vn
- VNeID docs: https://vneid.gov.vn
