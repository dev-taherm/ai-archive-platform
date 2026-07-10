const AGENT_BASE = "http://localhost:8420/api";

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const resp = await fetch(`${AGENT_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Agent API error ${resp.status}: ${body}`);
  }
  return resp.json();
}

export interface AgentStatus {
  agent_name: string;
  agent_id: string;
  version: string;
  uptime_seconds: number;
  watcher_active: boolean;
  watched_folders: string[];
  db_path: string;
  stats: {
    total: number;
    synced: number;
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
}

export interface AgentConfig {
  server_url: string;
  api_key: string;
  jwt_token: string;
  agent_name: string;
  agent_id: string;
  folders: string[];
  ocr_engine: string;
  ocr_lang: string;
  parser_backend: string;
  sync_interval_minutes: number;
}

export interface FileRecord {
  id: string;
  local_path: string;
  filename: string;
  extension: string;
  mime_type: string;
  size_bytes: number;
  content_hash: string;
  processing_status: string;
  synced: number;
  extracted_text: string;
  first_seen_at: string;
  updated_at: string;
}

export interface FolderInfo {
  path: string;
  label: string;
  exists: boolean;
  watching: boolean;
}

export const agentApi = {
  health: () => request<{ status: string }>("/health"),

  status: () => request<AgentStatus>("/status"),

  config: () => request<AgentConfig>("/config"),

  updateConfig: (config: Partial<AgentConfig>) =>
    request<{ status: string }>("/config", {
      method: "PUT",
      body: JSON.stringify(config),
    }),

  scan: (folder: string, recursive = true) =>
    request<{ scanned: number; processed: number; errors: number }>(
      "/scan",
      { method: "POST", body: JSON.stringify({ folder, recursive }) },
    ),

  process: (file: string) =>
    request<{ status: string; file: string; text_length: number }>(
      "/process",
      { method: "POST", body: JSON.stringify({ file }) },
    ),

  files: (status?: string, limit = 50) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    params.set("limit", String(limit));
    return request<{ files: FileRecord[]; count: number }>(
      `/files?${params}`,
    );
  },

  folders: () => request<{ folders: FolderInfo[] }>("/folders"),

  addFolder: (path: string) =>
    request<{ status: string; path: string }>("/folders", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  removeFolder: (path: string) =>
    request<{ status: string; path: string }>(
      `/folders/${encodeURIComponent(path)}`,
      { method: "DELETE" },
    ),

  logs: (lines = 100) =>
    request<{ logs: string[] }>(`/logs?lines=${lines}`),

  startWatcher: () =>
    request<{ status: string; folders?: string[]; message?: string }>(
      "/watch/start",
      { method: "POST" },
    ),

  stopWatcher: () =>
    request<{ status: string }>("/watch/stop", { method: "POST" }),

};
