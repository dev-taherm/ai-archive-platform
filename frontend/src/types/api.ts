export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface Document {
  id: string;
  title: string;
  filename: string;
  file_size: number;
  mime_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  tags: string[];
  summary: string | null;
  chunk_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SearchRequest {
  query: string;
  filters?: {
    tags?: string[];
    date_from?: string;
    date_to?: string;
    status?: Document["status"];
  };
  page?: number;
  page_size?: number;
}

export interface SearchResult {
  document_id: string;
  document_title: string;
  chunk_id: string;
  content: string;
  score: number;
  highlights: string[];
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  took_ms: number;
}

export interface DashboardStats {
  total_documents: number;
  total_chunks: number;
  total_searches: number;
  storage_used_bytes: number;
  documents_by_status: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  recent_activity: ActivityItem[];
  activity_over_time: ActivityTimeSeries[];
}

export interface ActivityItem {
  id: string;
  type: "upload" | "search" | "delete" | "update";
  description: string;
  document_id: string | null;
  created_at: string;
}

export interface ActivityTimeSeries {
  date: string;
  uploads: number;
  searches: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}
