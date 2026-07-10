import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";
import { agentApi } from "../lib/agent-api";
import type { AgentStatus, FileRecord, FolderInfo } from "../lib/agent-api";
import { useAuthStore } from "./auth-store";

interface AgentState {
  connected: boolean;
  status: AgentStatus | null;
  files: FileRecord[];
  folders: FolderInfo[];
  logs: string[];
  loading: boolean;
  error: string | null;

  fetchStatus: () => Promise<void>;
  fetchFiles: () => Promise<void>;
  fetchFolders: () => Promise<void>;
  fetchLogs: (lines?: number) => Promise<void>;
  scanFolder: (folder: string) => Promise<{ processed: number; errors: number }>;
  syncNow: () => Promise<void>;
  startWatcher: () => Promise<void>;
  stopWatcher: () => Promise<void>;
  addFolder: (path: string) => Promise<void>;
  removeFolder: (path: string) => Promise<void>;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  connected: false,
  status: null,
  files: [],
  folders: [],
  logs: [],
  loading: false,
  error: null,

  fetchStatus: async () => {
    try {
      const status = await agentApi.status();
      set({ connected: true, status, error: null });
    } catch {
      set({ connected: false, status: null });
    }
  },

  fetchFiles: async () => {
    try {
      const { files } = await agentApi.files(undefined, 50);
      set({ files });
    } catch {
      // keep existing
    }
  },

  fetchFolders: async () => {
    try {
      const { folders } = await agentApi.folders();
      set({ folders });
    } catch {
      // keep existing
    }
  },

  fetchLogs: async (lines = 100) => {
    try {
      const { logs } = await agentApi.logs(lines);
      set({ logs });
    } catch {
      // keep existing
    }
  },

  scanFolder: async (folder) => {
    set({ loading: true, error: null });
    try {
      const result = await agentApi.scan(folder);
      set({ loading: false });
      await get().fetchFiles();
      return result;
    } catch (e) {
      set({ loading: false, error: String(e) });
      return { processed: 0, errors: 1 };
    }
  },

  syncNow: async () => {
    set({ loading: true, error: null });
    try {
      const { serverUrl, agent } = useAuthStore.getState();
      if (!serverUrl || !agent) {
        throw new Error("Not authenticated");
      }
      await invoke("run_sync", {
        serverUrl,
        agentId: agent.agent_id,
        apiKey: agent.api_key,
        sidecarPort: 8420,
        batchSize: 50,
      });
      set({ loading: false });
      await get().fetchFiles();
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },

  startWatcher: async () => {
    try {
      await agentApi.startWatcher();
      await get().fetchStatus();
    } catch (e) {
      set({ error: String(e) });
    }
  },

  stopWatcher: async () => {
    try {
      await agentApi.stopWatcher();
      await get().fetchStatus();
    } catch (e) {
      set({ error: String(e) });
    }
  },

  addFolder: async (path) => {
    try {
      await agentApi.addFolder(path);
      await get().fetchFolders();
    } catch (e) {
      set({ error: String(e) });
    }
  },

  removeFolder: async (path) => {
    try {
      await agentApi.removeFolder(path);
      await get().fetchFolders();
    } catch (e) {
      set({ error: String(e) });
    }
  },
}));
