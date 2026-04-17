import type { TourStep } from "./index";

export const CITIZEN_PORTAL_TOUR: TourStep[] = [
  {
    element: '[data-tour="portal-ai-search"]',
    title: "Hỏi AI bằng ngôn ngữ thường",
    description:
      "Mô tả nhu cầu của anh/chị, AI sẽ gợi ý thủ tục phù hợp nhất. Ví dụ: 'Tôi muốn xin giấy phép xây nhà 3 tầng.'",
  },
  {
    element: '[data-tour="portal-tthc-cards"]',
    title: "Hoặc chọn thủ tục có sẵn",
    description:
      "5 thủ tục hành chính phổ biến nhất được liệt kê. Hover vào để xem chi tiết thành phần hồ sơ.",
    side: "top",
  },
  {
    element: '[data-tour="portal-stats"]',
    title: "Số liệu thực tế",
    description:
      "Hệ thống đã xử lý hàng nghìn hồ sơ. Con số cập nhật realtime từ cơ sở dữ liệu.",
    side: "top",
  },
  {
    element: '[data-tour="portal-chatbot"]',
    title: "Trợ lý AI luôn sẵn sàng",
    description:
      "Bấm vào bong bóng ở góc dưới phải bất cứ lúc nào để hỏi về thủ tục hoặc tra cứu hồ sơ.",
    side: "left",
  },
];
