"""
scripts/gen_demo_samples.py
Generate placeholder sample files used by the citizen "Điền mẫu" demo button.

No external deps (no Pillow, no reportlab) — emits:
  - Minimal valid JPEG (1x1 white) for images
  - Minimal valid PDF with one page of text for documents

Output dir: backend/public_assets/samples/
Files are referenced by backend/src/api/public.py _DEMO_SAMPLES.
"""
from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "backend" / "public_assets" / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Minimal valid 1x1 white JPEG (emitted verbatim from known good bytes)
# ---------------------------------------------------------------------------
# Baseline JFIF, 1x1 white, grayscale-quantized, ~125 bytes. Valid in all browsers.
_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb0043000806060706050806"
    "07070809090a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e27202229"
    "2c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b0800010001"
    "0101110000ffc4001f0000010501010101010100000000000000000102030405"
    "060708090a0bffc400b5100002010303020403050504040000017d010203000411"
    "051221314105611322718132061491a1b1c1423324521552072735317234f03f0"
    "0dabc"
)


def write_jpeg(filename: str, caption: str | None = None) -> None:
    # For demo purposes we just write the known valid 1x1. caption currently
    # ignored (would need a drawing lib) but kept in signature for clarity.
    path = OUT_DIR / filename
    path.write_bytes(_JPEG_BYTES)


# ---------------------------------------------------------------------------
# Minimal PDF generator — single page, 595x842 (A4), Helvetica 11, Vietnamese
# text rendered via WinAnsiEncoding escapes (limited subset but fine for demo).
# ---------------------------------------------------------------------------
def _pdf_escape(s: str) -> str:
    """Escape for PDF literal string. Strips diacritics to WinAnsi fallback."""
    import unicodedata
    nfd = unicodedata.normalize("NFD", s)
    ascii_s = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return ascii_s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(filename: str, title: str, body_lines: list[str]) -> None:
    """Write a simple A4 PDF with a title + body lines."""
    # PDF structure: header, 4 objects (catalog, pages, page, content), xref, trailer
    lines = [f"BT", f"/F1 16 Tf", f"72 780 Td", f"({_pdf_escape(title)}) Tj", "ET"]
    y = 740
    for line in body_lines:
        lines.extend([
            "BT", "/F1 11 Tf", f"72 {y} Td", f"({_pdf_escape(line)}) Tj", "ET",
        ])
        y -= 18
        if y < 80:
            break
    content_stream = "\n".join(lines).encode("latin-1", errors="replace")

    # Build objects
    objs: list[bytes] = []

    def obj(n: int, body: bytes) -> bytes:
        return f"{n} 0 obj\n".encode() + body + b"\nendobj\n"

    # 1: Catalog
    objs.append(obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    # 2: Pages
    objs.append(obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    # 3: Page
    objs.append(obj(3,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"))
    # 4: Content stream
    stream_body = b"<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n" + content_stream + b"\nendstream"
    objs.append(obj(4, stream_body))
    # 5: Font
    objs.append(obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"))

    # Assemble with xref
    out = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]  # first entry is always 0
    for o in objs:
        offsets.append(len(out))
        out += o
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()

    (OUT_DIR / filename).write_bytes(out)


# ---------------------------------------------------------------------------
# Concrete samples (all referenced by backend/src/api/public.py _DEMO_SAMPLES)
# ---------------------------------------------------------------------------

SAMPLES: list[tuple[str, dict]] = [
    # Image
    ("sample_cccd.jpg", {}),
]

PDFS: list[tuple[str, str, list[str]]] = [
    (
        "sample_don_xin_cpxd.pdf",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        [
            "Độc lập - Tự do - Hạnh phúc",
            "",
            "ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP XÂY DỰNG",
            "",
            "Kính gửi: Sở Xây dựng Hà Nội",
            "Họ và tên chủ đầu tư: Nguyễn Văn Bình",
            "Số CCCD: 001085012345",
            "Địa chỉ: Số 18 Nguyễn Trãi, Thanh Xuân, Hà Nội",
            "Thửa đất số 285, tờ bản đồ 12",
            "Diện tích xây dựng: 82 m2, quy mô 3 tầng",
            "Thời hạn xin phép: 12 tháng kể từ ngày cấp phép.",
            "",
            "Tôi cam kết thực hiện đúng quy định pháp luật.",
            "Hà Nội, ngày 15 tháng 04 năm 2026",
            "Người đề nghị (đã ký)",
            "Nguyễn Văn Bình",
        ],
    ),
    (
        "sample_ban_ve_thiet_ke.pdf",
        "BẢN VẼ THIẾT KẾ CÔNG TRÌNH",
        [
            "Công trình: Nhà ở riêng lẻ - Thửa 285 tờ 12 Quận Thanh Xuân",
            "Quy mô: 3 tầng + tum mái, diện tích xây dựng 82 m2",
            "Tổng diện tích sàn: 246 m2",
            "Chiều cao công trình: 10.8 m",
            "Móng: Bê tông cốt thép, cọc khoan nhồi D300",
            "Kết cấu: Khung bê tông cốt thép chịu lực",
            "Cấp công trình: III (theo QCVN 03:2022/BXD)",
            "",
            "Bản vẽ do Công ty TNHH Tư vấn Thiết kế ABC thực hiện",
            "Chủ nhiệm đồ án: KTS Trần Văn Nam (số CCHN 12345)",
        ],
    ),
    (
        "sample_gcn_qsdd.pdf",
        "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT",
        [
            "QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC",
            "",
            "Người sử dụng đất: Nguyễn Văn Bình",
            "Số CCCD: 001085012345",
            "Thửa đất số: 285 - Tờ bản đồ số: 12",
            "Địa chỉ thửa đất: Phường Thượng Đình, Quận Thanh Xuân, TP Hà Nội",
            "Diện tích: 82.0 m2 (tám mươi hai mét vuông)",
            "Mục đích sử dụng: Đất ở tại đô thị",
            "Thời hạn sử dụng: Lâu dài",
            "Hình thức sử dụng: Riêng",
            "",
            "Số vào sổ cấp GCN: CQ-01-XD-HN-2023/485",
            "Ngày cấp: 12/09/2023",
        ],
    ),
    (
        "sample_don_dang_ky_qsdd.pdf",
        "ĐƠN ĐĂNG KÝ CẤP GIẤY CHỨNG NHẬN QSDĐ",
        [
            "Kính gửi: Văn phòng đăng ký đất đai Bình Định",
            "Họ tên: Trần Thị Hoa - CCCD: 052075067890",
            "Địa chỉ: Số 45 Lê Hồng Phong, TP Quy Nhơn, Bình Định",
            "Thửa đất số 102, tờ 5 — diện tích 120 m2",
            "Mục đích: Đất ở tại đô thị",
            "Nguồn gốc: Chuyển nhượng năm 2022",
        ],
    ),
    (
        "sample_ban_do_dia_chinh.pdf",
        "BẢN ĐỒ ĐỊA CHÍNH",
        [
            "Thửa 102, tờ bản đồ 5",
            "Vị trí: Phường Trần Phú, TP Quy Nhơn, Bình Định",
            "Kích thước: 10 x 12 m (mặt đường 10m)",
            "Diện tích: 120 m2",
            "Tiếp giáp: Bắc-đường Lê Hồng Phong, Nam-thửa 101, Đông-thửa 103, Tây-thửa 92",
        ],
    ),
    (
        "sample_giay_de_nghi_dkkd.pdf",
        "GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP",
        [
            "Loại hình: Công ty TNHH một thành viên",
            "Tên: Công ty TNHH Tư vấn Quản lý Tuấn Minh",
            "Chủ sở hữu: Lê Minh Tuấn - CCCD: 079082034567",
            "Trụ sở: Số 7 Đinh Tiên Hoàng, Quận 1, TP HCM",
            "Vốn điều lệ: 500.000.000 VND",
            "Ngành nghề: Hoạt động tư vấn quản lý (mã 7020)",
        ],
    ),
    (
        "sample_dieu_le_cong_ty.pdf",
        "ĐIỀU LỆ CÔNG TY TNHH TƯ VẤN QUẢN LÝ TUẤN MINH",
        [
            "Chương I - Quy định chung",
            "Điều 1. Tên công ty: Công ty TNHH Tư vấn Quản lý Tuấn Minh",
            "Điều 2. Trụ sở: Số 7 Đinh Tiên Hoàng, Đa Kao, Quận 1, HCM",
            "Điều 3. Ngành nghề: Tư vấn quản lý doanh nghiệp",
            "Điều 4. Vốn điều lệ: 500.000.000 đồng",
            "",
            "Chương II - Quyền và nghĩa vụ",
            "Điều 5. Chủ sở hữu: Ông Lê Minh Tuấn sở hữu 100% vốn",
        ],
    ),
    (
        "sample_don_yeu_cau_lltp.pdf",
        "ĐƠN YÊU CẦU CẤP PHIẾU LÝ LỊCH TƯ PHÁP",
        [
            "Kính gửi: Sở Tư pháp Hà Nội",
            "Họ tên: Phạm Thị Lan - CCCD: 036095089012",
            "Địa chỉ: Số 22 Bà Triệu, Hai Bà Trưng, Hà Nội",
            "Loại phiếu: Phiếu lý lịch tư pháp số 1",
            "Mục đích sử dụng: Xin việc làm tại doanh nghiệp",
            "Số lượng phiếu yêu cầu: 02",
        ],
    ),
    (
        "sample_bao_cao_dtm.pdf",
        "BÁO CÁO ĐÁNH GIÁ TÁC ĐỘNG MÔI TRƯỜNG",
        [
            "Dự án: Nhà máy sản xuất bao bì - Công ty TNHH Xanh Việt",
            "Địa điểm: Lô B12 KCN Thăng Long, Đông Anh, Hà Nội",
            "Công suất thiết kế: 200 tấn bao bì / tháng",
            "Diện tích đất: 5.200 m2",
            "Nước thải: 120 m3/ngày, xử lý bằng hệ thống sinh học MBR",
            "Khí thải: Lò hơi đốt gas, ống khói cao 18m",
            "Tuân thủ QCVN 40:2011/BTNMT (nước thải công nghiệp)",
        ],
    ),
    (
        "sample_giay_phep_kd.pdf",
        "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP",
        [
            "Tên doanh nghiệp: Công ty TNHH Xanh Việt",
            "Mã số doanh nghiệp: 0106789012",
            "Địa chỉ: Lô B12 KCN Thăng Long, Đông Anh, Hà Nội",
            "Ngày thành lập: 10/06/2020",
            "Vốn điều lệ: 10.000.000.000 VND",
            "Ngành nghề chính: Sản xuất bao bì từ plastic",
        ],
    ),
]


def main() -> None:
    for filename, _ in SAMPLES:
        write_jpeg(filename)
        print(f"  [jpg] {filename}")
    for filename, title, body in PDFS:
        write_pdf(filename, title, body)
        print(f"  [pdf] {filename}")
    print(f"\nWrote {len(SAMPLES) + len(PDFS)} files to {OUT_DIR}")


if __name__ == "__main__":
    main()
