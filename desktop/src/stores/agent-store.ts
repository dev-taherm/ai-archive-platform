import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

export interface FileRecord {
  id: string;
  local_path: string;
  filename: string;
  extension: string;
  file_hash: string;
  size_bytes: number;
  mime_type: string;
  modified_at: string;
  processing_status: string;
  extracted_text: string;
  markdown: string;
  content_blocks: string;
  tables: string;
  images: string;
  language: string;
  word_count: number;
  char_count: number;
  page_count: number;
  synced: boolean;
  first_seen_at: string;
  updated_at: string;
}

export interface FolderInfo {
  path: string;
  label: string;
  exists: boolean;
}

export interface TrashEntry {
  id: string;
  original_path: string;
  filename: string;
  deleted_at: string;
  size_bytes: number;
  trash_file_exists: boolean;
}

interface AgentMetrics {
  files_scanned: number;
  parse_time_total_ms: number;
  parse_errors: number;
  sync_events: number;
  sync_files: number;
  heartbeat_count: number;
  memory_mb: number;
}

interface AgentState {
  connected: boolean;
  files: FileRecord[];
  folders: FolderInfo[];
  loading: boolean;
  error: string | null;
  selectedFiles: Set<string>;
  processingFiles: Set<string>;
  logs: string[];
  metrics: AgentMetrics | null;
  trash: TrashEntry[];
  paused: boolean;
  startError: string | null;

  fetchLogs: (lines?: number) => Promise<void>;
  fetchStatus: () => Promise<void>;
  fetchStartError: () => Promise<void>;
  fetchFiles: () => Promise<void>;
  fetchFolders: () => Promise<void>;
  fetchMetrics: () => Promise<void>;
  fetchTrash: () => Promise<void>;
  syncNow: () => Promise<void>;
  startAgent: () => Promise<void>;
  stopAgent: () => Promise<void>;
  pauseAgent: () => Promise<void>;
  resumeAgent: () => Promise<void>;
  addFolder: (path: string) => Promise<void>;
  removeFolder: (path: string) => Promise<void>;
  scanFile: (fileId: string) => Promise<void>;
  scanSelected: () => Promise<void>;
  moveFile: (fileId: string, destPath: string) => Promise<void>;
  renameFile: (fileId: string, newName: string) => Promise<void>;
  deleteFile: (fileId: string) => Promise<void>;
  copyFile: (fileId: string, destPath: string) => Promise<void>;
  archiveFiles: (fileIds: string[], destPath: string, format?: string) => Promise<void>;
  restoreFile: (trashId: string) => Promise<void>;
  permanentlyDeleteFile: (trashId: string) => Promise<void>;
  toggleFileSelection: (fileId: string) => void;
  selectAllFiles: () => void;
  clearSelection: () => void;
  _clearError: () => void;
  _setError: (msg: string) => void;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  connected: false,
  files: [],
  logs: [],
  folders: [],
  loading: false,
  error: null,
  metrics: null,
  trash: [],
  paused: false,
  startError: null,
  selectedFiles: new Set(),
  processingFiles: new Set(),

  _clearError: () => set({ error: null }),

  _setError: (msg: string) => {
    set({ error: msg });
    setTimeout(() => set({ error: null }), 5000);
  },

  fetchStartError: async () => {
    try {
      const err = await invoke<string | null>("get_agent_start_error");
      set({ startError: err });
    } catch {
      // ignore
    }
  },

  fetchStatus: async () => {
    try {
      const running = await invoke<boolean>("agent_health");
      if (running) {
        const status = await invoke<{ worker?: { paused?: boolean } }>("call_agent_api", {
          method: "GET", path: "/api/status", body: null,
        });
        set({ connected: true, paused: status.worker?.paused ?? false, error: null, startError: null });
      } else {
        set({ connected: false });
      }
    } catch {
      set({ connected: false });
    }
  },

  fetchFiles: async () => {
    try {
      const files = await invoke<FileRecord[]>("get_files", { status: null, limit: 1000 });
      set({ files });
    } catch {
      // keep existing
    }
  },

  fetchFolders: async () => {
    try {
      const folders = await invoke<FolderInfo[]>("get_folders");
      set({ folders });
    } catch {
      // keep existing
    }
  },

  syncNow: async () => {
    set({ loading: true, error: null });
    try {
      await invoke("run_sync");
      set({ loading: false });
      await get().fetchFiles();
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },

  startAgent: async () => {
    set({ loading: true, error: null });
    try {
      await invoke("start_agent");
      await new Promise(r => setTimeout(r, 2000));
      await get().fetchStatus();
      set({ loading: false });
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },

  stopAgent: async () => {
    set({ loading: true, error: null });
    try {
      await invoke("stop_agent");
      set({ connected: false, loading: false });
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },

  addFolder: async (path) => {
    try {
      await invoke("add_folder", { path });
      await get().fetchFolders();
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  fetchLogs: async (_lines?: number) => {
    try {
      const entries = await invoke<{ timestamp: string; level: string; logger: string; message: string }[]>("call_agent_api", {
        method: "GET",
        path: `/api/logs?limit=${_lines || 200}`,
        body: null,
      });
      set({ logs: entries.map(e => `[${e.level}] ${e.message}`) });
    } catch {
      // keep existing
    }
  },

  removeFolder: async (path) => {
    try {
      await invoke("remove_folder", { path });
      await get().fetchFolders();
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  scanFile: async (fileId: string) => {
    const processing = new Set(get().processingFiles);
    processing.add(fileId);
    set({ processingFiles: processing, error: null });
    try {
      const result = await invoke<{ status: string; file_id?: string; job_id?: string }>("scan_file", { fileId });
      if (result.status === "processing" && result.job_id) {
        await _pollJob(result.job_id);
      }
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    } finally {
      const updated = new Set(get().processingFiles);
      updated.delete(fileId);
      set({ processingFiles: updated });
    }
  },

  moveFile: async (fileId: string, destPath: string) => {
    try {
      await invoke("move_file", { fileId, destPath });
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  renameFile: async (fileId: string, newName: string) => {
    try {
      await invoke("rename_file", { fileId, newName });
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  deleteFile: async (fileId: string) => {
    try {
      await invoke("delete_file", { fileId });
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  copyFile: async (fileId: string, destPath: string) => {
    try {
      await invoke("copy_file", { fileId, destPath });
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  archiveFiles: async (fileIds: string[], destPath: string, format: string = "zip") => {
    try {
      await invoke("archive_files", { fileIds, destPath, format });
    } catch (e) {
      get()._setError(String(e));
    }
  },

  restoreFile: async (trashId: string) => {
    try {
      await invoke("restore_file", { trashId });
      await get().fetchFiles();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  getTrash: async () => {
    try {
      return await invoke<{ id: string; original_path: string; filename: string; deleted_at: string }[]>("get_trash");
    } catch {
      return [];
    }
  },

  scanSelected: async () => {
    const selected = Array.from(get().selectedFiles);
    if (selected.length === 0) return;
    set({ loading: true, error: null });
    try {
      await invoke<{ status: string }>("scan_selected", { fileIds: selected });
      set({ loading: false, selectedFiles: new Set() });
      await get().fetchFiles();
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },

  fetchMetrics: async () => {
    try {
      const metrics = await invoke<AgentMetrics & { status?: string }>("call_agent_api", {
        method: "GET",
        path: "/api/metrics",
        body: null,
      });
      set({ metrics: { ...metrics, memory_mb: metrics.memory_mb || 0 } });
    } catch {
      // keep existing
    }
  },

  fetchTrash: async () => {
    try {
      const trash = await invoke<TrashEntry[]>("get_trash");
      set({ trash });
    } catch {
      // keep existing
    }
  },

  pauseAgent: async () => {
    try {
      await invoke("call_agent_api", { method: "POST", path: "/api/agent/pause", body: null });
      set({ paused: true });
    } catch (e) {
      get()._setError(String(e));
    }
  },

  resumeAgent: async () => {
    try {
      await invoke("call_agent_api", { method: "POST", path: "/api/agent/resume", body: null });
      set({ paused: false });
    } catch (e) {
      get()._setError(String(e));
    }
  },

  permanentlyDeleteFile: async (trashId: string) => {
    try {
      await invoke("call_agent_api", {
        method: "DELETE",
        path: `/api/trash/${trashId}`,
        body: null,
      });
      await get().fetchTrash();
    } catch (e) {
      get()._setError(String(e));
    }
  },

  toggleFileSelection: (fileId: string) => {
    const selected = new Set(get().selectedFiles);
    if (selected.has(fileId)) {
      selected.delete(fileId);
    } else {
      selected.add(fileId);
    }
    set({ selectedFiles: selected });
  },

  selectAllFiles: () => {
    const selected = new Set(get().files.map(f => f.id));
    set({ selectedFiles: selected });
  },

  clearSelection: () => {
    set({ selectedFiles: new Set() });
  },
}));

async function _pollJob(jobId: string, maxAttempts = 60): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const job = await invoke<{ status: string }>("call_agent_api", {
        method: "GET",
        path: `/api/jobs/${jobId}`,
        body: null,
      });
      if (job.status === "completed" || job.status === "failed") return;
    } catch {
      return;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
}
