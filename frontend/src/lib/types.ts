/* TypeScript types mirroring backend/src/models/schemas.py and enums.py */

// ---- Enums ----
export enum ClearanceLevel {
  UNCLASSIFIED = 0,
  CONFIDENTIAL = 1,
  SECRET = 2,
  TOP_SECRET = 3,
}

export enum CaseStatus {
  SUBMITTED = "submitted",
  CLASSIFYING = "classifying",
  EXTRACTING = "extracting",
  GAP_CHECKING = "gap_checking",
  PENDING_SUPPLEMENT = "pending_supplement",
  LEGAL_REVIEW = "legal_review",
  DRAFTING = "drafting",
  LEADER_REVIEW = "leader_review",
  CONSULTATION = "consultation",
  APPROVED = "approved",
  REJECTED = "rejected",
  PUBLISHED = "published",
}

export enum Role {
  ADMIN = "admin",
  LEADER = "leader",
  OFFICER = "officer",
  STAFF_INTAKE = "staff_intake",
  STAFF_PROCESSOR = "staff_processor",
  LEGAL = "legal",
  SECURITY = "security",
  PUBLIC_VIEWER = "public_viewer",
}

export enum NotificationCategory {
  INFO = "info",
  ACTION_REQUIRED = "action_required",
  ALERT = "alert",
  SYSTEM = "system",
}

// ---- Auth ----
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  role: string;
  clearance_level: number;
  full_name?: string;
}

export interface User {
  user_id: string;
  username: string;
  full_name?: string;
  role: string;
  clearance_level: number;
  departments: string[];
}

// ---- Cases ----
export interface CaseCreate {
  tthc_code: string;
  department_id: string;
  applicant_name: string;
  applicant_id_number: string;
  applicant_phone?: string;
  applicant_address?: string;
  notes?: string;
}

export interface CaseResponse {
  case_id: string;
  code: string;
  status: CaseStatus;
  tthc_code: string;
  department_id: string;
  submitted_at: string;
  applicant_name: string;
  processing_days: number | null;
  sla_days: number | null;
  is_overdue: boolean;
}

export interface CaseListResponse {
  items: CaseResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ---- Bundles / Documents ----
export interface BundleFileInfo {
  filename: string;
  content_type: string;
  size_bytes: number;
}

export interface BundleCreate {
  files: BundleFileInfo[];
}

export interface UploadURL {
  filename: string;
  signed_url: string;
  oss_key: string;
}

export interface BundleResponse {
  bundle_id: string;
  case_id: string;
  upload_urls: UploadURL[];
  status: string;
}

export interface DocumentResponse {
  doc_id: string;
  filename: string;
  content_type: string;
  page_count: number | null;
  ocr_status: string;
  oss_key: string;
}

// ---- Agents ----
export interface AgentRunRequest {
  pipeline?: string;
}

export interface AgentStepResponse {
  step_id: string;
  agent_name: string;
  action: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  input_tokens: number;
  output_tokens: number;
  tool_calls: number;
}

export interface AgentTraceResponse {
  case_id: string;
  steps: AgentStepResponse[];
  status: string;
  total_tokens: number;
  total_duration_ms: number;
}

// ---- Graph ----
export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface SubgraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ---- Search ----
export interface LawSearchResult {
  chunk_id: string;
  law_id: string;
  article_number: string;
  clause_path: string;
  content: string;
  similarity: number;
}

export interface TTHCSearchResult {
  tthc_code: string;
  name: string;
  department: string;
  sla_days: number;
  required_components: string[];
}

// ---- Notifications ----
export interface NotificationResponse {
  id: string;
  title: string;
  body: string | null;
  category: NotificationCategory;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

// ---- Leadership ----
export interface AgentPerformanceItem {
  agent_name: string;
  total_runs: number;
  avg_duration_ms: number;
  avg_tokens: number;
}

export interface DashboardResponse {
  total_cases: number;
  pending_cases: number;
  overdue_cases: number;
  completed_today: number;
  avg_processing_days: number;
  cases_by_status: Record<string, number>;
  cases_by_department: Record<string, number>;
  agent_performance: AgentPerformanceItem[];
}

export interface InboxItem {
  case_id: string;
  code: string;
  title: string;
  action_required: string;
  priority: string;
  created_at: string;
}

// ---- Audit ----
export interface AuditEventResponse {
  id: string;
  event_type: string;
  actor_name: string | null;
  target_type: string | null;
  target_id: string | null;
  case_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

// ---- Public ----
export interface PublicCaseStatus {
  code: string;
  status: string;
  submitted_at: string;
  current_step: string | null;
  estimated_completion: string | null;
  /** Optional – populated when backend returns them */
  sla_days?: number;
  processing_days?: number;
}

export interface PublicTTHCItem {
  tthc_code: string;
  name: string;
  department: string;
  sla_days: number;
  fee: string;
  required_components: string[];
}

export interface PublicStatsResponse {
  total_cases_processed: number;
  avg_processing_days: number;
  cases_this_month: number;
  satisfaction_rate: number | null;
}

// ---- WebSocket ----
export interface WSMessage {
  topic: string;
  event: string;
  data: unknown;
}

// ---- Chat / AI Assistant ----
export type ChatRole = "user" | "assistant" | "system" | "tool";

export interface ToolCall {
  id: string;
  name: string;
  args?: Record<string, unknown>;
  status: "pending" | "success" | "error";
  result?: unknown;
  durationMs?: number;
}

/** Citation used in chat messages and AI recommendation cards */
export interface Citation {
  id: string;
  lawName: string;
  article: string;
  url?: string;
  chunkId?: string;
}

export interface Attachment {
  id: string;
  name: string;
  url?: string;
  type: "image" | "pdf" | "other";
}

export interface Entity {
  key: string;
  value: unknown;
  confidence: number;
  bbox?: number[];
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  citations?: Citation[];
  attachments?: Attachment[];
}
