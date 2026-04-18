#!/usr/bin/env python3
"""
Regenerate sample PDF + JPEG files with real Vietnamese content + upload
to MinIO bucket so judges actually see something when they click "Xem tài liệu".

Two outputs:

1. /backend/public_assets/samples/ — quick-fill template files served at
   /public/samples/<name>. Used by intake page "Điền mẫu (demo)" button.

2. govflow-dev MinIO bucket → documents/{CASE-ID}/{DOC-ID}/<filename> —
   per Document vertex's oss_key. Replaces the existing 299-byte empty
   PDF shells.

Run after seed_demo_extended.py. Idempotent.

Usage:
    backend/.venv/bin/python scripts/regenerate_sample_files.py [--dry-run]
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path
from typing import Iterable

import boto3
from botocore.client import Config
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Make backend src importable for live GDB query
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# ---------------------------------------------------------------------------
# Vietnamese font registration
# ---------------------------------------------------------------------------
# DejaVu ships with most Linux distros + supports Vietnamese diacritics fully.

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]
_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]


def _register_fonts() -> tuple[str, str]:
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont("VnSans", path))
            regular = "VnSans"
            break
    for path in _FONT_BOLD_CANDIDATES:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont("VnSans-Bold", path))
            bold = "VnSans-Bold"
            break
    return regular, bold


FONT_REG, FONT_BOLD = _register_fonts()


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------
def build_admin_pdf(
    title: str,
    organisation: str,
    body_lines: Iterable[str],
    *,
    document_no: str = "Số: 01/2026/ĐĐN",
    place_date: str = "Hà Nội, ngày 18 tháng 04 năm 2026",
    signer_role: str = "Người làm đơn",
    signer_name: str = "Nguyễn Văn Bình",
) -> bytes:
    """Render a Vietnamese admin form PDF following ND 30/2020 layout."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    left = 2 * cm
    right = width - 2 * cm
    y = height - 2 * cm

    # Quốc hiệu — tiêu ngữ
    c.setFont(FONT_BOLD, 12)
    c.drawCentredString(width / 2, y, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    y -= 16
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(width / 2, y, "Độc lập – Tự do – Hạnh phúc")
    y -= 6
    c.line(width / 2 - 90, y, width / 2 + 90, y)
    y -= 22

    # Cơ quan ban hành (left) + ngày tháng (right)
    c.setFont(FONT_BOLD, 10)
    c.drawString(left, y, organisation)
    c.setFont(FONT_REG, 10)
    c.drawRightString(right, y, place_date)
    y -= 14
    c.setFont(FONT_REG, 10)
    c.drawString(left, y, document_no)
    y -= 26

    # Title
    c.setFont(FONT_BOLD, 16)
    c.drawCentredString(width / 2, y, title.upper())
    y -= 28

    # Body
    c.setFont(FONT_REG, 11)
    for line in body_lines:
        if y < 4 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont(FONT_REG, 11)
        # Wrap at 95 chars roughly
        chunk = line.strip()
        while chunk:
            piece = chunk[:95]
            c.drawString(left, y, piece)
            y -= 16
            chunk = chunk[95:]
        y -= 4

    # Signature block
    if y < 5 * cm:
        c.showPage()
        y = height - 2 * cm
    y -= 10
    c.setFont(FONT_BOLD, 11)
    c.drawRightString(right, y, signer_role.upper())
    y -= 14
    c.setFont(FONT_REG, 9)
    c.drawRightString(right, y, "(Ký, ghi rõ họ tên / [Ký số CA])")
    y -= 50
    c.setFont(FONT_BOLD, 11)
    c.drawRightString(right, y, signer_name)

    c.save()
    return buf.getvalue()


def build_cccd_jpeg(
    full_name: str = "NGUYỄN VĂN BÌNH",
    cccd_no: str = "001 085 012 345",
    dob: str = "15/03/1985",
    gender: str = "Nam",
    nationality: str = "Việt Nam",
    home_town: str = "Hưng Yên",
    address: str = "Số 18 Nguyễn Trãi, Thượng Đình, Thanh Xuân, Hà Nội",
) -> bytes:
    """Render a stylised CCCD (citizen ID) front-side as JPEG."""
    W, H = 1012, 638  # 85x53mm @ 12dpi-ish
    img = Image.new("RGB", (W, H), (235, 244, 255))
    d = ImageDraw.Draw(img)

    # Try Vietnamese-capable font, fallback default
    try:
        font_path = next(
            (p for p in _FONT_CANDIDATES if Path(p).exists()),
            None,
        )
        font_path_bold = next(
            (p for p in _FONT_BOLD_CANDIDATES if Path(p).exists()),
            font_path,
        )
        f_title = ImageFont.truetype(font_path_bold or font_path, 28) if font_path else ImageFont.load_default()
        f_label = ImageFont.truetype(font_path or "DejaVuSans", 18) if font_path else ImageFont.load_default()
        f_value = ImageFont.truetype(font_path_bold or font_path, 22) if font_path else ImageFont.load_default()
        f_small = ImageFont.truetype(font_path or "DejaVuSans", 14) if font_path else ImageFont.load_default()
    except Exception:
        f_title = f_label = f_value = f_small = ImageFont.load_default()

    # Header strip
    d.rectangle([0, 0, W, 90], fill=(0, 70, 166))
    d.text((20, 10), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", font=f_title, fill=(255, 255, 255))
    d.text((20, 50), "Độc lập – Tự do – Hạnh phúc", font=f_label, fill=(220, 230, 255))

    d.text((20, 110), "CĂN CƯỚC CÔNG DÂN", font=f_title, fill=(0, 70, 166))
    d.text((20, 145), "Citizen Identity Card", font=f_small, fill=(80, 80, 80))

    # Photo placeholder box
    d.rectangle([720, 110, 980, 410], outline=(0, 70, 166), width=3)
    d.text((780, 240), "ẢNH", font=f_title, fill=(160, 180, 200))
    d.text((760, 280), "PHOTO", font=f_label, fill=(160, 180, 200))

    # Fields
    rows = [
        ("Số / No.:", cccd_no),
        ("Họ và tên / Full name:", full_name),
        ("Ngày sinh / DOB:", dob),
        ("Giới tính / Sex:", gender),
        ("Quốc tịch / Nationality:", nationality),
        ("Quê quán / Home town:", home_town),
        ("Nơi thường trú / Permanent residence:", address),
    ]
    y = 200
    for label, value in rows:
        d.text((20, y), label, font=f_small, fill=(70, 90, 120))
        y += 22
        d.text((20, y), value, font=f_value, fill=(20, 20, 30))
        y += 30

    # Footer note + watermark
    d.text((20, H - 50), "Có giá trị đến / Valid until: 15/03/2050", font=f_small, fill=(80, 80, 80))
    d.text((20, H - 28), "DEMO - GovFlow sample - không có giá trị pháp lý", font=f_small, fill=(180, 30, 30))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Sample template specs (used for /public/samples + per-doc overrides)
# ---------------------------------------------------------------------------
SAMPLE_TEMPLATES: dict[str, dict] = {
    "sample_don_xin_cpxd.pdf": {
        "title": "Đơn đề nghị cấp giấy phép xây dựng",
        "organisation": "UBND THÀNH PHỐ HÀ NỘI\nSỞ XÂY DỰNG",
        "document_no": "Số: 145/2026/CPXD",
        "body": [
            "Kính gửi: Sở Xây dựng thành phố Hà Nội",
            "",
            "Họ và tên chủ đầu tư: Nguyễn Văn Bình",
            "Số CCCD: 001085012345 — Cấp ngày 12/04/2021 tại Cục Cảnh sát QLHC",
            "Địa chỉ thường trú: Số 18 Nguyễn Trãi, Thượng Đình, Thanh Xuân, Hà Nội",
            "Số điện thoại: 0912 345 678",
            "",
            "Đề nghị cấp giấy phép xây dựng cho công trình:",
            "  · Tên công trình: Nhà ở riêng lẻ 3 tầng",
            "  · Địa điểm: Lô đất A12, Khu đô thị Văn Phú, phường Phú La, quận Hà Đông, Hà Nội",
            "  · Diện tích sàn: 240 m² (3 tầng × 80 m²)",
            "  · Mật độ xây dựng: 65%",
            "  · Chiều cao công trình: 11,4 mét (3 tầng + tum)",
            "",
            "Hồ sơ kèm theo:",
            "  1. Bản vẽ thiết kế cơ sở (kèm theo)",
            "  2. Giấy chứng nhận quyền sử dụng đất số CT-78912 cấp ngày 02/06/2023",
            "  3. Hợp đồng thiết kế với Công ty CP Kiến trúc HanoiPlan, ký 14/03/2026",
            "  4. Báo cáo kết quả thẩm tra thiết kế của UBND quận Hà Đông",
            "",
            "Tôi cam đoan thực hiện đúng theo nội dung giấy phép được cấp, tuân thủ Luật",
            "Xây dựng 2014, Nghị định 15/2021/NĐ-CP và các quy định hiện hành về phòng",
            "cháy chữa cháy theo Nghị định 136/2020/NĐ-CP.",
        ],
    },
    "sample_ban_ve_thiet_ke.pdf": {
        "title": "Bản vẽ thiết kế cơ sở",
        "organisation": "CÔNG TY CP KIẾN TRÚC HANOIPLAN",
        "document_no": "Số: BVTK-2026-0145",
        "body": [
            "Công trình: Nhà ở riêng lẻ 3 tầng",
            "Chủ đầu tư: Nguyễn Văn Bình",
            "Địa điểm: Lô A12, KĐT Văn Phú, Hà Đông, Hà Nội",
            "",
            "1. Tổng quan công trình",
            "  · Loại công trình: Nhà ở riêng lẻ, cấp III",
            "  · Diện tích đất: 100 m²",
            "  · Diện tích xây dựng: 65 m²",
            "  · Tổng diện tích sàn: 240 m² (3 tầng + tum sân thượng)",
            "  · Chiều cao công trình: 11,4 m",
            "  · Mật độ xây dựng: 65% (theo quy hoạch khu đô thị)",
            "",
            "2. Giải pháp kiến trúc",
            "  · Phong cách: Hiện đại, tận dụng ánh sáng tự nhiên",
            "  · Mặt đứng chính hướng Đông Nam, ban công 1,2 m mỗi tầng",
            "  · Tầng 1: phòng khách + bếp + WC chung + 1 phòng ngủ",
            "  · Tầng 2: 2 phòng ngủ master + WC riêng + phòng làm việc",
            "  · Tầng 3: 1 phòng ngủ + phòng thờ + sân phơi",
            "",
            "3. Giải pháp kết cấu",
            "  · Móng: Móng đơn cọc khoan nhồi D300, sâu 12 m",
            "  · Cột, dầm: Bê tông cốt thép M250, thép CB300V",
            "  · Tường gạch đặc M75, vữa xi măng M50",
            "  · Sàn bê tông cốt thép dày 100 mm",
            "",
            "4. Giải pháp PCCC (theo NĐ 136/2020/NĐ-CP)",
            "  · Cầu thang thoát hiểm rộng 1,2 m, có cửa chống cháy EI60",
            "  · 4 bình chữa cháy MFZ4 đặt tại các tầng",
            "  · Hệ thống báo cháy tự động kết nối UBND phường",
        ],
        "signer_role": "Kiến trúc sư trưởng",
        "signer_name": "KTS. Lê Quang Anh",
    },
    "sample_gcn_qsdd.pdf": {
        "title": "Giấy chứng nhận quyền sử dụng đất",
        "organisation": "UBND THÀNH PHỐ HÀ NỘI\nSỞ TÀI NGUYÊN VÀ MÔI TRƯỜNG",
        "document_no": "Số: CT-78912 / 2023",
        "body": [
            "Người sử dụng đất: Nguyễn Văn Bình",
            "Số CCCD: 001 085 012 345",
            "Địa chỉ: Số 18 Nguyễn Trãi, Thượng Đình, Thanh Xuân, Hà Nội",
            "",
            "Thửa đất số: A12 — Tờ bản đồ số: 24",
            "Địa chỉ thửa đất: KĐT Văn Phú, phường Phú La, quận Hà Đông, Hà Nội",
            "Diện tích: 100 m² (Một trăm mét vuông)",
            "Hình thức sử dụng: Sử dụng riêng",
            "Mục đích sử dụng: Đất ở tại đô thị (ODT)",
            "Thời hạn sử dụng: Lâu dài",
            "Nguồn gốc sử dụng: Nhận chuyển nhượng quyền sử dụng đất",
            "",
            "Tài sản gắn liền với đất: Chưa có công trình",
            "",
            "Cấp ngày: 02/06/2023",
            "Cơ quan cấp: Sở Tài nguyên và Môi trường thành phố Hà Nội",
            "Quyết định số: 1247/QĐ-STNMT ngày 28/05/2023",
        ],
        "signer_role": "Giám đốc Sở",
        "signer_name": "Trần Thị Lan Anh",
    },
    "sample_don_dang_ky_qsdd.pdf": {
        "title": "Đơn đăng ký cấp Giấy chứng nhận QSDĐ",
        "organisation": "VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI HÀ NỘI",
        "document_no": "Số: 87/2026/ĐKĐĐ",
        "body": [
            "Kính gửi: Văn phòng Đăng ký đất đai thành phố Hà Nội",
            "",
            "Họ tên người đề nghị: Trần Thị Hoa",
            "Số CCCD: 024090123456 — Cấp ngày 22/05/2022",
            "Địa chỉ: Số 45 Lê Lợi, phường Bến Nghé, quận 1, TP. Hồ Chí Minh",
            "",
            "Đề nghị cấp Giấy chứng nhận quyền sử dụng đất cho thửa đất:",
            "  · Số thửa: 145, Tờ bản đồ số: 32",
            "  · Địa chỉ: Khu phố 4, phường Long Trường, TP. Thủ Đức",
            "  · Diện tích: 145 m²",
            "  · Mục đích sử dụng: Đất ở tại đô thị",
            "  · Nguồn gốc: Nhận chuyển nhượng theo HĐ số 2856/HĐCN ngày 14/02/2024",
            "",
            "Hồ sơ kèm theo: hợp đồng chuyển nhượng công chứng, biên bản đo đạc địa",
            "chính, giấy nộp lệ phí trước bạ, sơ đồ thửa đất.",
        ],
    },
    "sample_ban_do_dia_chinh.pdf": {
        "title": "Trích lục bản đồ địa chính",
        "organisation": "VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI HÀ NỘI",
        "document_no": "Số: TLBĐ-2026-145",
        "body": [
            "Trích lục bản đồ địa chính thửa đất số 145, tờ bản đồ số 32",
            "Địa chỉ: Khu phố 4, phường Long Trường, TP. Thủ Đức",
            "",
            "Toạ độ ranh giới (VN-2000):",
            "  Điểm 1: X = 1.190.452,12 ; Y = 681.245,56",
            "  Điểm 2: X = 1.190.471,88 ; Y = 681.249,92",
            "  Điểm 3: X = 1.190.476,03 ; Y = 681.234,17",
            "  Điểm 4: X = 1.190.456,27 ; Y = 681.229,81",
            "",
            "Diện tích: 145,00 m²",
            "Mục đích sử dụng: ODT (Đất ở tại đô thị)",
            "Loại đất theo quy hoạch: Đất ở mật độ thấp",
            "Trạng thái pháp lý: Đã cấp GCN số CT-89712/2022",
        ],
        "signer_role": "Trưởng văn phòng",
        "signer_name": "KS. Phạm Đức Hùng",
    },
    "sample_giay_de_nghi_dkkd.pdf": {
        "title": "Giấy đề nghị đăng ký doanh nghiệp",
        "organisation": "SỞ KẾ HOẠCH VÀ ĐẦU TƯ HÀ NỘI",
        "document_no": "Số: 312/2026/ĐKDN",
        "body": [
            "Kính gửi: Phòng Đăng ký kinh doanh — Sở KH&ĐT Hà Nội",
            "",
            "Tên doanh nghiệp: CÔNG TY TNHH XANH VIỆT",
            "Tên viết tắt: XANH VIỆT CO., LTD",
            "Loại hình: Công ty TNHH một thành viên",
            "Địa chỉ trụ sở chính: Số 88 Trần Hưng Đạo, phường Cửa Nam, quận Hoàn Kiếm, Hà Nội",
            "Vốn điều lệ: 5.000.000.000 VNĐ (Năm tỷ đồng)",
            "",
            "Ngành nghề kinh doanh chính:",
            "  · 4690 — Bán buôn tổng hợp",
            "  · 4711 — Bán lẻ tại siêu thị, cửa hàng tiện lợi",
            "  · 8230 — Tổ chức giới thiệu và xúc tiến thương mại",
            "",
            "Người đại diện theo pháp luật:",
            "  · Họ tên: Lê Minh Tuấn",
            "  · Số CCCD: 030198765432",
            "  · Chức danh: Tổng Giám đốc kiêm Chủ tịch",
            "",
            "Cam kết: Doanh nghiệp xin cam kết thực hiện đúng quy định của Luật Doanh",
            "nghiệp 2020 (59/2020/QH14) và các quy định pháp luật khác có liên quan.",
        ],
    },
    "sample_dieu_le_cong_ty.pdf": {
        "title": "Điều lệ Công ty TNHH Xanh Việt",
        "organisation": "CÔNG TY TNHH XANH VIỆT",
        "document_no": "Số: 01/2026/ĐL-XV",
        "body": [
            "ĐIỀU LỆ CÔNG TY TNHH MỘT THÀNH VIÊN",
            "",
            "CHƯƠNG I — NHỮNG QUY ĐỊNH CHUNG",
            "Điều 1. Tên doanh nghiệp",
            "  Tên đầy đủ: CÔNG TY TNHH XANH VIỆT",
            "  Tên giao dịch quốc tế: XANH VIET CO., LTD",
            "",
            "Điều 2. Hình thức và mục đích",
            "  Công ty được tổ chức dưới hình thức TNHH một thành viên theo Luật Doanh",
            "  nghiệp 2020. Mục đích: tối đa hoá lợi ích của chủ sở hữu thông qua hoạt",
            "  động kinh doanh hợp pháp.",
            "",
            "Điều 3. Vốn điều lệ và sở hữu",
            "  · Vốn điều lệ: 5.000.000.000 VNĐ",
            "  · Chủ sở hữu duy nhất: Lê Minh Tuấn (CCCD 030198765432)",
            "",
            "CHƯƠNG II — CƠ CẤU TỔ CHỨC",
            "Điều 4. Hội đồng thành viên / Chủ sở hữu",
            "  Chủ sở hữu thực hiện đầy đủ quyền và nghĩa vụ theo Điều 76 Luật DN 2020.",
            "",
            "Điều 5. Giám đốc / Tổng Giám đốc",
            "  Do chủ sở hữu bổ nhiệm, nhiệm kỳ tối đa 5 năm.",
        ],
    },
    "sample_don_yeu_cau_lltp.pdf": {
        "title": "Đơn yêu cầu cấp Phiếu lý lịch tư pháp",
        "organisation": "SỞ TƯ PHÁP HÀ NỘI",
        "document_no": "Số: 2024-LLTP-9871",
        "body": [
            "Kính gửi: Sở Tư pháp thành phố Hà Nội",
            "",
            "Họ và tên: Phạm Thị Lan",
            "Ngày sinh: 22/09/1992",
            "Giới tính: Nữ",
            "Quốc tịch: Việt Nam",
            "Nơi sinh: Tỉnh Nghệ An",
            "Số CCCD: 042192876543 — cấp ngày 18/01/2023",
            "Địa chỉ thường trú: Số 12 Nguyễn Du, phường Bùi Thị Xuân, quận Hai Bà Trưng",
            "",
            "Yêu cầu cấp: Phiếu lý lịch tư pháp số 1 (dành cho cá nhân)",
            "Mục đích sử dụng: Bổ sung hồ sơ xin việc tại Ngân hàng Vietcombank",
            "",
            "Tôi cam đoan các thông tin khai trên là đúng sự thật, nếu sai tôi xin chịu",
            "trách nhiệm trước pháp luật theo quy định của Luật Lý lịch tư pháp 2009.",
        ],
        "signer_role": "Người yêu cầu",
        "signer_name": "Phạm Thị Lan",
    },
    "sample_giay_phep_kd.pdf": {
        "title": "Giấy chứng nhận đăng ký doanh nghiệp",
        "organisation": "SỞ KẾ HOẠCH VÀ ĐẦU TƯ HÀ NỘI",
        "document_no": "Số: 0107654321",
        "body": [
            "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP",
            "Công ty TNHH một thành viên",
            "",
            "1. Tên công ty: CÔNG TY TNHH XANH VIỆT",
            "2. Mã số doanh nghiệp: 0107654321",
            "3. Địa chỉ trụ sở chính: Số 88 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội",
            "4. Vốn điều lệ: 5.000.000.000 VNĐ",
            "",
            "5. Người đại diện theo pháp luật:",
            "  · Họ tên: Lê Minh Tuấn — Chức danh: Tổng Giám đốc",
            "  · Số CCCD: 030198765432",
            "",
            "6. Đăng ký lần đầu: 18/04/2026",
            "7. Đăng ký thay đổi lần thứ: 0",
            "",
            "Doanh nghiệp được phép hoạt động theo các ngành nghề đã đăng ký, tuân thủ",
            "Luật Doanh nghiệp 2020 và các quy định pháp luật liên quan.",
        ],
        "signer_role": "Trưởng phòng ĐKKD",
        "signer_name": "Đỗ Trung Kiên",
    },
    "sample_bao_cao_dtm.pdf": {
        "title": "Báo cáo đánh giá tác động môi trường",
        "organisation": "CÔNG TY CP MÔI TRƯỜNG XANH SÁNG",
        "document_no": "Số: ĐTM-2026-2154",
        "body": [
            "Tên dự án: Nhà máy chế biến nông sản XANH VIỆT — giai đoạn 1",
            "Chủ đầu tư: Công ty TNHH XANH VIỆT",
            "Địa điểm dự án: KCN Quang Minh, Mê Linh, Hà Nội",
            "Tổng diện tích: 12.500 m²",
            "Vốn đầu tư: 85 tỷ đồng",
            "",
            "I. Tóm tắt tác động môi trường",
            "  · Khí thải: phát sinh từ lò hơi 5 tấn/giờ; xử lý qua hệ thống cyclone +",
            "    túi vải đạt QCVN 19:2009/BTNMT cột B.",
            "  · Nước thải: 60 m³/ngày sinh hoạt + 120 m³/ngày sản xuất; xử lý qua bể",
            "    sinh học hiếu khí + lắng + khử trùng đạt QCVN 40:2011/BTNMT cột A.",
            "  · Chất thải rắn: 800 kg/ngày, phân loại nguồn, hợp đồng xử lý URENCO.",
            "  · Tiếng ồn: ≤ 70 dBA tại ranh giới khu vực sản xuất.",
            "",
            "II. Biện pháp giảm thiểu",
            "  · Lắp đặt hệ thống quan trắc khí thải tự động liên tục, truyền dữ liệu",
            "    trực tiếp về Sở TN&MT theo Thông tư 10/2021/TT-BTNMT.",
            "  · Trồng dải cây xanh cách ly 5 m quanh khu sản xuất.",
            "  · Đào tạo định kỳ ATVSLĐ + ứng phó sự cố môi trường mỗi 6 tháng.",
            "",
            "III. Cam kết tuân thủ",
            "  Chủ đầu tư cam kết tuân thủ Luật Bảo vệ môi trường 2020 (72/2020/QH14)",
            "  và Nghị định 08/2022/NĐ-CP, đồng thời chịu trách nhiệm trước pháp luật",
            "  về tính chính xác của báo cáo này.",
        ],
        "signer_role": "Tư vấn lập báo cáo",
        "signer_name": "TS. Nguyễn Hữu Phú",
    },
}


# ---------------------------------------------------------------------------
# Per-document overrides — match seeded oss_keys to a template
# ---------------------------------------------------------------------------
def template_for_filename(oss_filename: str) -> str:
    """Map an oss_key filename → sample template key."""
    name = oss_filename.lower()
    if "ban-ve" in name or "thiet-ke" in name or "banve" in name:
        return "sample_ban_ve_thiet_ke.pdf"
    if "gcn" in name and ("qsd" in name or "su-dung-dat" in name):
        return "sample_gcn_qsdd.pdf"
    if "dia-chinh" in name or "ban-do" in name:
        return "sample_ban_do_dia_chinh.pdf"
    if "dieu-le" in name:
        return "sample_dieu_le_cong_ty.pdf"
    if "dang-ky" in name and "qsd" in name:
        return "sample_don_dang_ky_qsdd.pdf"
    if "lltp" in name or "ly-lich-tu-phap" in name:
        return "sample_don_yeu_cau_lltp.pdf"
    if "giay-phep-kd" in name or ("dkkd" in name and "kd" in name):
        return "sample_giay_phep_kd.pdf"
    if "dkkd" in name or "dang-ky-doanh-nghiep" in name or "dang-ky-kd" in name:
        return "sample_giay_de_nghi_dkkd.pdf"
    if "dieu-le" in name or "cong-ty" in name:
        return "sample_dieu_le_cong_ty.pdf"
    if "dtm" in name or "moi-truong" in name or "danh-gia-tac-dong" in name:
        return "sample_bao_cao_dtm.pdf"
    if "hop-dong" in name:
        # Generic admin form
        return "sample_dieu_le_cong_ty.pdf"
    # Default — use đơn xin CPXD as it's the most generic
    return "sample_don_xin_cpxd.pdf"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(dry_run: bool = False) -> None:
    samples_dir = Path(__file__).resolve().parent.parent / "backend" / "public_assets" / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Generating {len(SAMPLE_TEMPLATES)} sample template files into {samples_dir}")
    cache: dict[str, bytes] = {}
    for fname, spec in SAMPLE_TEMPLATES.items():
        pdf = build_admin_pdf(
            title=spec["title"],
            organisation=spec["organisation"],
            body_lines=spec["body"],
            document_no=spec.get("document_no", "Số: 01/2026"),
            signer_role=spec.get("signer_role", "Người làm đơn"),
            signer_name=spec.get("signer_name", "Nguyễn Văn Bình"),
        )
        cache[fname] = pdf
        if not dry_run:
            (samples_dir / fname).write_bytes(pdf)
        print(f"     {fname}: {len(pdf):,} bytes")

    # Generate JPG sample CCCD
    cccd_bytes = build_cccd_jpeg()
    cache["sample_cccd.jpg"] = cccd_bytes
    if not dry_run:
        (samples_dir / "sample_cccd.jpg").write_bytes(cccd_bytes)
    print(f"     sample_cccd.jpg: {len(cccd_bytes):,} bytes")

    # ----- Step 2: Pull all Document oss_keys from GDB -----
    print("\n[2/3] Reading all Document vertices from GDB")
    from gremlin_python.driver import client as _gclient

    gdb = _gclient.Client("ws://localhost:8182/gremlin", "g")
    docs = gdb.submit(
        "g.V().hasLabel('Document').valueMap('doc_id','oss_key','filename','content_type').toList()"
    ).all().result()
    gdb.close()
    print(f"     Found {len(docs)} Document vertices")

    # ----- Step 3: Upload to MinIO -----
    print("\n[3/3] Uploading to MinIO bucket govflow-dev")
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://localhost:9100"),
        aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin123"),
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    bucket = "govflow-dev"

    uploaded = 0
    skipped = 0
    for d in docs:
        oss_key = d.get("oss_key", [None])
        oss_key = oss_key[0] if isinstance(oss_key, list) else oss_key
        if not oss_key:
            skipped += 1
            continue
        content_type = d.get("content_type", ["application/pdf"])
        content_type = content_type[0] if isinstance(content_type, list) else content_type

        # Pick template by filename hint in the oss_key
        filename = Path(oss_key).name
        if content_type == "image/jpeg" or filename.lower().endswith((".jpg", ".jpeg")):
            payload = cache["sample_cccd.jpg"]
            ctype = "image/jpeg"
        else:
            tmpl_key = template_for_filename(filename)
            payload = cache[tmpl_key]
            ctype = "application/pdf"

        if dry_run:
            print(f"     DRY: {oss_key} ← {tmpl_key if ctype == 'application/pdf' else 'sample_cccd.jpg'} ({len(payload):,}B)")
        else:
            s3.put_object(
                Bucket=bucket,
                Key=oss_key,
                Body=payload,
                ContentType=ctype,
            )
        uploaded += 1

    print(f"\n     Uploaded {uploaded} objects · skipped {skipped} (missing oss_key)")
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
