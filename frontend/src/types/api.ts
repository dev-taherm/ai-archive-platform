// ============================================================
// Types matching Django backend responses
// ============================================================

// --- Auth ---

export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
  user: User;
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

export interface Document {
  id: string;
  file_id: string;
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
}

export interface ActivityItem {
  id: string;
  type: "upload" | "search" | "delete" | "update";
  description: string;
  document_id: string | null;
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

// --- Common ---

export interface ApiError {
  detail: string;
  status_code?: number;
}
