export const HELP_CONTENT = {
  // Inbox
  "inbox-kanban-drag":
    "Kéo thả thẻ hồ sơ giữa các cột để chuyển trạng thái xử lý. AI sẽ tự động ghi lại lịch sử và cập nhật SLA.",
  "inbox-filter":
    "Dùng bộ lọc 'Sắp hết hạn' để ưu tiên hồ sơ gần SLA. Cột màu đỏ là quá hạn.",

  // Compliance
  "compliance-ai-recommendation":
    "AI đề xuất quyết định dựa trên 4 agents: DocAnalyzer (Qwen3-VL), Compliance, LegalLookup (GraphRAG), và Summarizer. Bấm 'AI suy nghĩ gì?' để xem reasoning.",
  "compliance-citation":
    "Bấm vào điều luật để xem nội dung đầy đủ. Citation được trích bởi LegalLookup agent qua tìm kiếm GraphRAG trên Knowledge Graph.",

  // Trace
  "trace-graph":
    "Đồ thị tri thức hiển thị các thực thể (Case, Document, Gap, Citation) và quan hệ. Click node để xem chi tiết.",
  "trace-replay":
    "Bấm 'Phát lại' để xem pipeline AI chạy lại từ đầu với tốc độ 1×, 2×, hoặc 4×.",

  // Dashboard
  "dashboard-kpi-pending":
    "Số hồ sơ đang ở các stage trung gian (chưa hoàn thành, chưa từ chối). KPI này phản ánh khối lượng công việc thực tế.",
  "dashboard-kpi-overdue":
    "Hồ sơ đã quá deadline SLA. Cảnh báo đỏ khi >5%.",
  "dashboard-agent-perf":
    "Hiệu suất 10 AI agents — số lần chạy, thời gian trung bình, token sử dụng. Giúp đánh giá chi phí AI.",
  "dashboard-ai-report":
    "Báo cáo tuần do AI tổng hợp tự động từ dữ liệu xử lý — thay vì cán bộ phải tổng hợp tay.",

  // Intake
  "intake-upload":
    "Kéo thả file hồ sơ vào đây. Qwen3-VL sẽ tự động OCR + trích xuất thông tin (họ tên, CCCD, địa chỉ).",
  "intake-pipeline":
    "Sau upload, 10 agents AI sẽ chạy song song: phân loại TTHC, kiểm tra tuân thủ, tra cứu luật, định tuyến cơ quan...",

  // Security
  "security-3-tier":
    "GovFlow có 3 tầng phân quyền: SDK Guard (parse Gremlin AST), GDB RBAC (database-level), Property Mask (field-level redaction).",

  // Portal (citizen)
  "portal-ai-search":
    "Hãy mô tả nhu cầu bằng ngôn ngữ thường — AI sẽ gợi ý thủ tục phù hợp. Ví dụ: 'Tôi muốn xin giấy phép xây nhà 3 tầng.'",
  "portal-chatbot":
    "Bấm vào nút trợ lý AI ở góc dưới phải để hỏi bất kỳ câu nào về thủ tục.",

  // Submit wizard
  "submit-ai-fill":
    "Tải lên ảnh CCCD — AI sẽ tự động điền họ tên, số CCCD, ngày sinh. Bạn chỉ cần kiểm tra lại.",
  "submit-precheck":
    "Trước khi nộp, bấm 'AI kiểm tra hồ sơ' để phát hiện sớm thiếu sót.",

  // Track
  "track-explanation":
    "AI giải thích trạng thái hồ sơ bằng tiếng Việt phổ thông, kèm bước tiếp theo nếu cần làm.",
} as const;

export type HelpContentKey = keyof typeof HELP_CONTENT;
