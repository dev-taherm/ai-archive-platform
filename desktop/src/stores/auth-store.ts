import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

interface AgentInfo {
  agent_id: string;
  api_key: string;
}

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  refreshToken: string | null;
  serverUrl: string;
  webUrl: string;
  configLoaded: boolean;
  agent: AgentInfo | null;
  login: (serverUrl: string, token: string, refreshToken?: string) => void;
  logout: () => void;
  setAgent: (agent: AgentInfo) => void;
  loadServerConfig: () => Promise<void>;
  tryRegisterAgent: () => Promise<void>;
}

let heartbeatInterval: ReturnType<typeof setInterval> | null = null;
let syncInterval: ReturnType<typeof setInterval> | null = null;

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: !!localStorage.getItem("token"),
  token: localStorage.getItem("token"),
  refreshToken: localStorage.getItem("refreshToken"),
  serverUrl: localStorage.getItem("serverUrl") || "",
  webUrl: "",
  configLoaded: false,
  agent: (() => {
    try { return JSON.parse(localStorage.getItem("agent") || "null"); } catch { return null; }
  })(),
  login: (serverUrl, token, refreshToken) => {
    localStorage.setItem("token", token);
    localStorage.setItem("serverUrl", serverUrl);
    if (refreshToken) localStorage.setItem("refreshToken", refreshToken);
    set({ isAuthenticated: true, token, refreshToken: refreshToken || null, serverUrl });
    _startBackgroundTasks(get);
  },
  logout: () => {
    _stopBackgroundTasks();
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("serverUrl");
    localStorage.removeItem("agent");
    set({ isAuthenticated: false, token: null, refreshToken: null, agent: null });
  },
  setAgent: (agent) => {
    localStorage.setItem("agent", JSON.stringify(agent));
    set({ agent });
  },
  loadServerConfig: async () => {
    if (get().configLoaded) return;
    try {
      const config = await invoke<{ server_url: string; web_url: string }>("read_server_config");
      const webUrl = config.web_url || config.server_url;
      if (config.server_url && !get().serverUrl) {
        set({ serverUrl: config.server_url, webUrl, configLoaded: true });
      } else {
        set({ webUrl, configLoaded: true });
      }
    } catch {
      set({ configLoaded: true });
    }
    tryRegisterAgent(get);
  },
  tryRegisterAgent: async () => {
    const { isAuthenticated, serverUrl, token, agent } = get();
    if (isAuthenticated && serverUrl && token && !agent) {
      try {
        const result = await invoke<{ agent_id: string; api_key: string }>("register_agent", {
          serverUrl,
          accessToken: token,
        });
        get().setAgent(result);
        _startBackgroundTasks(get);
      } catch (e) {
        console.warn("Auto-register failed:", e);
        _stopBackgroundTasks();
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        localStorage.removeItem("serverUrl");
        localStorage.removeItem("agent");
        set({ isAuthenticated: false, token: null, refreshToken: null, serverUrl: "", agent: null });
      }
    }
  },
}));

function _startBackgroundTasks(get: () => AuthState) {
  if (heartbeatInterval || syncInterval) return;

  heartbeatInterval = setInterval(async () => {
    const { serverUrl, agent } = get();
    if (!serverUrl || !agent) return;
    try {
      await invoke("send_heartbeat", {
        serverUrl,
        agentId: agent.agent_id,
        apiKey: agent.api_key,
        filesCount: 0,
      });
    } catch (e) {
      console.warn("Heartbeat failed:", e);
    }
  }, 60_000);

  syncInterval = setInterval(async () => {
    const { serverUrl, agent } = get();
    if (!serverUrl || !agent) return;
    try {
      await invoke("run_sync", {
        serverUrl,
        agentId: agent.agent_id,
        apiKey: agent.api_key,
        sidecarPort: 8420,
        batchSize: 50,
      });
    } catch (e) {
      console.warn("Sync failed:", e);
    }
  }, 300_000); // 5 minutes
}

function _stopBackgroundTasks() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
}
