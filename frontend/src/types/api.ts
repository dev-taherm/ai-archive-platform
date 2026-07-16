// ============================================================
// Types matching Django backend responses
// ============================================================

// --- Auth ---

export interface OrgMembership {
  id: string;
  name: string;
  slug: string;
  role: "owner" | "admin" | "member";
}

export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
  current_organization: string | null;
  organization_name: string | null;
  organization_slug: string | null;
  org_role: "owner" | "admin" | "member" | null;
  organizations: OrgMembership[];
}

export interface AuthTokens {
  access: string;
  refresh: string;
  user: User;
}

export interface SwitchOrgRequest {
  organization_id: string;
}

export interface SwitchOrgResponse {
  access: string;
  refresh: string;
  organization: Organization;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  password_confirm: string;
  username: string;
  first_name?: string;
  last_name?: string;
  invitation_token?: string;
}

// --- Files ---

export interface FileRecord {
  id: string;
  path: string;
  mime_type: string;
  size_bytes: number;
  status: "pending" | "indexing" | "completed" | "failed";
  checksum: string;
  tags: string[];
  metadata: Record<string, unknown>;
  duplicate_group_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScanRequest {
  folder_path: string;
  recursive?: boolean;
  patterns?: string[];
  ignore_patterns?: string[];
}

export interface ScanResult {
  folder_path: string;
  total_files_found: number;
  files_scanned: number;
  new_files: number;
  skipped_files: number;
  failed_files: number;
  scan_duration_seconds: number;
  scanned_at: string;
  errors: string[];
  file_ids: string[];
}

export type ScanProgressEventType =
  | "scan_started"
  | "file_scanned"
  | "scan_complete"
  | "scan_error";

export interface ScanProgressEvent {
  event: ScanProgressEventType;
  data: {
    message?: string;
    folder_path?: string;
    processed?: number;
    total_found?: number;
    current_file?: string;
    new?: number;
    skipped?: number;
    failed?: number;
    files_scanned?: number;
    new_files?: number;
    skipped_files?: number;
    failed_files?: number;
    scan_duration_seconds?: number;
    errors?: string[];
    detail?: string;
  };
}

export interface FileOperationResult {
  operation: string;
  file_id: string;
  source_path: string;
  destination_path: string | null;
  success: boolean;
  error_message: string | null;
  performed_at: string;
}

// --- Documents ---

export interface DocumentEntity {
  name: string;
  type: string;
  context: string;
}

export interface DocumentMetadata {
  title: string;
  author: string;
  subject: string;
  keywords: string[];
  creation_date: string;
  modification_date: string;
  page_count: number;
  word_count: number;
  char_count: number;
  language: string;
  extra: Record<string, unknown>;
}

export interface SiblingDocument {
  id: string;
  document_index: number;
  title: string;
}

export interface Document {
  id: string;
  file_id: string;
  document_index: number;
  page_start: number | null;
  page_end: number | null;
  total_documents_for_file: number;
  file_name: string;
  file_path: string;
  file_mime_type: string;
  doc_type: string;
  processing_status: "queued" | "extracting" | "classifying" | "indexing" | "completed" | "failed" | "retrying";
  title: string;
  author: string;
  subject: string;
  language: string;
  word_count: number;
  page_count: number;
  chunk_count: number;
  classification_confidence: number | null;
  tags: string[];
  extracted_text_preview: string;
  error_message: string | null;
  entities?: DocumentEntity[];
  summary?: string;
  sibling_documents?: SiblingDocument[];
  created_at: string;
  updated_at: string;
}

// --- Search ---

export interface SearchRequest {
  query: string;
  search_type?: "hybrid" | "semantic" | "keyword";
  max_results?: number;
  offset?: number;
  filters?: {
    doc_types?: string[];
    languages?: string[];
    tags?: string[];
    date_from?: string;
    date_to?: string;
    min_score?: number;
    file_extensions?: string[];
    exclude_duplicates?: boolean;
  };
}

export interface SearchResult {
  document_id: string;
  file_id: string;
  title: string;
  snippet: string;
  score: number;
  rank: number;
  doc_type: string;
  language: string;
  match_source: string;
  highlights: string[];
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_count: number;
  search_time_ms: number;
  search_type: string;
}

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  search_type: string;
  filters: Record<string, unknown>;
  created_at: string;
}

export interface SearchHistoryEntry {
  id: string;
  query: string;
  search_type: string;
  result_count: number;
  search_time_ms: number;
  filters_used: Record<string, unknown>;
  created_at: string;
}

// --- Dashboard ---

export interface DashboardStats {
  total_files: number;
  total_documents: number;
  total_searches: number;
  total_chat_sessions: number;
  files_by_status: Record<string, number>;
  documents_by_type: Record<string, number>;
  documents_by_status: Record<string, number>;
  recent_uploads_count: number;
  storage_used_bytes: number;
  avg_processing_time_ms: number;
  agents_total: number;
  agents_online: number;
  duplicate_files: number;
  duplicate_groups: number;
}

export interface ActivityItem {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  user_email: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface ActivityResponse {
  activities: ActivityItem[];
  total_count: number;
}

export interface ChartDataPoint {
  date: string;
  uploads: number;
  searches: number;
}

// --- Pipeline ---

export interface PipelineResult {
  status: string;
  document_id: string;
  parse_method: string;
  classification: string;
  classification_confidence: number;
  entities: { name: string; type: string; context: string }[];
  summary: string;
  chunk_count: number;
  embedding_count: number;
  processing_log: string[];
  error: string | null;
}

// --- AI ---

export interface ClassificationResult {
  document_id: string;
  predicted_type: string;
  confidence: number;
  all_labels: string[];
  model_used: string;
  classified_at: string;
}

// --- Providers ---

export interface ProviderConfig {
  id: string;
  name: string;
  display_name: string;
  provider_type: "openai" | "google" | "ollama";
  capabilities: ("llm" | "embedding")[];
  api_key_set: boolean;
  api_key?: string;
  base_url: string;
  model_name: string;
  is_active: boolean;
  is_default: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// --- Agents ---

export interface AgentFolder {
  id: string;
  local_path: string;
  label: string;
  is_active: boolean;
  last_scanned_at: string | null;
  file_count: number;
}

export interface AgentCommand {
  id: string;
  command_type: string;
  payload: Record<string, unknown>;
  status: "pending" | "delivered" | "completed" | "failed";
  result: string | null;
  created_at: string;
  executed_at: string | null;
}

export interface Agent {
  id: string;
  agent_id: string;
  name: string;
  status: "online" | "offline" | "syncing" | "error";
  platform: string;
  hostname: string;
  ip_address: string;
  agent_version: string;
  capabilities: string[];
  last_seen: string | null;
  last_sync_at: string | null;
  files_count: number;
  sync_scope: "personal" | "organization";
  total_size_bytes: number;
  sync_interval_minutes: number;
  max_file_size_mb: number;
  folders: AgentFolder[];
  pending_commands_count: number;
  created_at: string;
  updated_at: string;
}

export interface AgentSetupResponse {
  jwt_token: string;
  server_url: string;
  download_url: string;
  existing_agents_count: number;
}

export interface AgentDownloadManifest {
  version: string;
  builds: Record<
    string,
    {
      filename: string;
      size_bytes: number;
      sha256: string;
      built_at: string;
    }
  >;
}

export interface DesktopBuildManifest {
  version: string;
  builds: Record<
    string,
    {
      filename: string;
      size_bytes: number;
      sha256: string;
      built_at: string;
    }
  >;
}

// --- Common ---

export interface ApiError {
  detail: string;
  status_code?: number;
}

// --- Tools ---

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

// --- Recommendations ---

export interface Recommendation {
  id: string;
  type: "action" | "insight" | "warning";
  title: string;
  description: string;
  action_label: string | null;
  action_url: string | null;
  priority: "high" | "medium" | "low";
  count: number | null;
}

export interface RecommendationList {
  recommendations: Recommendation[];
  generated_at: string;
}

// --- Organizations ---

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  id: string;
  user: string;
  user_email: string;
  user_username: string;
  organization: string;
  role: "owner" | "admin" | "member";
  joined_at: string;
}

export interface Invitation {
  id: string;
  organization: string;
  email: string;
  role: "owner" | "admin" | "member";
  invited_by_email: string;
  status: "pending" | "accepted" | "expired" | "revoked";
  token: string;
  created_at: string;
  expires_at: string;
}

// Workflow types
export interface WorkflowStep {
  id: string;
  name: string;
  type: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: "draft" | "active" | "paused" | "completed" | "failed";
  trigger: string;
  steps: WorkflowStep[];
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  status: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  current_step: number;
  total_steps: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

// Chat types
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ document_id: string; title: string; snippet: string }>;
  tool_calls?: ToolCall[];
}

export interface Session {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

// Report types
export interface ReportData {
  storage: {
    total_files: number;
    total_size_bytes: number;
    by_type: Record<string, { count: number; size_bytes: number }>;
  };
  processing: {
    total_processed: number;
    success_rate: number;
    avg_time_ms: number;
    by_status: Record<string, number>;
  };
  activity: {
    daily_uploads: { date: string; count: number }[];
    top_tags: { tag: string; count: number }[];
    recent_reports: {
      id: string;
      name: string;
      type: string;
      generated_at: string;
      file_size: number;
    }[];
  };
}

// API Key type
export interface ApiKey {
  id: string;
  name: string;
  key_preview: string;
  created_at: string;
  last_used: string | null;
}

// Entity aggregation type
export interface EntityAgg {
  name: string;
  type: string;
  count: number;
  documents: { id: string; title: string }[];
}
