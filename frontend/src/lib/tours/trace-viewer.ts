import type { TourStep } from "./index";

export const TRACE_VIEWER_TOUR: TourStep[] = [
  {
    element: '[data-tour="trace-graph"]',
    title: "Đồ thị Knowledge Graph",
    description:
      "Hiển thị tất cả thực thể (Case, Document, Gap, Citation) và mối quan hệ giữa chúng. Click vào node để xem chi tiết.",
    side: "right",
  },
  {
    element: '[data-tour="trace-steps"]',
    title: "Các bước xử lý AI",
    description:
      "Pipeline 10 agents chạy tuần tự/song song. Mỗi bước hiển thị agent, mô hình AI, thời gian và chi phí token.",
    side: "left",
  },
  {
    element: '[data-tour="trace-replay"]',
    title: "Phát lại pipeline AI",
    description:
      "Bấm để xem lại toàn bộ quá trình AI xử lý từ đầu — hữu ích để kiểm tra và debug reasoning.",
    side: "bottom",
  },
];
