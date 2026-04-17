import type { TourStep } from "./index";

export const LEADER_DASHBOARD_TOUR: TourStep[] = [
  {
    element: '[data-tour="dashboard-kpis"]',
    title: "KPI tổng quan",
    description:
      "4 chỉ số chính: Tổng hồ sơ, Đang xử lý, Quá hạn, Thời gian TB. Hover (?) để xem định nghĩa chính xác.",
    side: "bottom",
  },
  {
    element: '[data-tour="dashboard-ai-report"]',
    title: "Báo cáo tuần do AI tổng hợp",
    description:
      "AI tự động phân tích dữ liệu xử lý và tạo báo cáo — thay vì cán bộ phải tổng hợp tay mỗi tuần.",
    side: "top",
  },
  {
    element: '[data-tour="dashboard-agent-perf"]',
    title: "Hiệu suất 10 AI Agents",
    description:
      "Theo dõi số lần chạy, thời gian trung bình và token tiêu thụ của từng agent. Giúp đánh giá chi phí AI vận hành.",
    side: "top",
  },
];
