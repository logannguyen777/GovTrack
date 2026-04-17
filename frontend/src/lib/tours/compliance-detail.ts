import type { TourStep } from "./index";

export const COMPLIANCE_DETAIL_TOUR: TourStep[] = [
  {
    element: '[data-tour="compliance-ai-rec"]',
    title: "Đề xuất AI",
    description:
      "Tổng hợp từ 4 agents: DocAnalyzer (Qwen3-VL), Compliance, LegalLookup (GraphRAG), Summarizer. Bấm 'AI suy nghĩ gì?' để xem toàn bộ reasoning.",
    side: "left",
  },
  {
    element: '[data-tour="compliance-citations"]',
    title: "Điều luật liên quan",
    description:
      "Citation được trích bởi LegalLookup agent qua GraphRAG. Bấm vào từng điều luật để xem nội dung đầy đủ từ Knowledge Graph.",
    side: "left",
  },
  {
    element: '[data-tour="compliance-gaps"]',
    title: "Lỗ hổng tuân thủ",
    description:
      "Các thiếu sót trong hồ sơ do Compliance agent phát hiện, kèm gợi ý bổ sung. Màu cam/đỏ = nghiêm trọng.",
    side: "top",
  },
];
