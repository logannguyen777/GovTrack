import type { TourStep } from "./index";

export const OFFICER_INBOX_TOUR: TourStep[] = [
  {
    element: '[data-tour="inbox-kanban"]',
    title: "Bảng Kanban xử lý hồ sơ",
    description:
      "5 cột đại diện 5 giai đoạn xử lý: Tiếp nhận → Đang xử lý → Chờ ý kiến → Đã quyết định → Trả kết quả.",
    side: "top",
  },
  {
    element: '[data-tour="inbox-filter"]',
    title: "Bộ lọc thông minh",
    description:
      "Lọc theo 'Sắp hạn' để ưu tiên hồ sơ gần deadline SLA. Lọc 'Quá hạn' để xử lý khẩn cấp ngay.",
    side: "bottom",
  },
  {
    element: '[data-tour="inbox-drag-hint"]',
    title: "Kéo thả để chuyển trạng thái",
    description:
      "Dùng nút ≡ ở trái thẻ để kéo hồ sơ sang cột khác. AI tự động ghi lịch sử và cập nhật SLA sau mỗi lần chuyển.",
    side: "right",
  },
];
