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
  },
  logout: () => {
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
      const config = await invoke<Record<string, string>>("get_config");
      const webUrl = config.frontend_url || config.web_url || "";
      if (config.server_url && !get().serverUrl) {
        set({ serverUrl: config.server_url, webUrl, configLoaded: true });
      } else {
        set({ webUrl, configLoaded: true });
      }
    } catch {
      const saved = localStorage.getItem("serverUrl");
      if (saved) {
        set({ serverUrl: saved, configLoaded: true });
      } else {
        set({ configLoaded: true });
      }
    }
    get().tryRegisterAgent();
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
      } catch (e) {
        console.warn("Auto-register failed:", e);
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        localStorage.removeItem("serverUrl");
        localStorage.removeItem("agent");
        set({ isAuthenticated: false, token: null, refreshToken: null, serverUrl: "", agent: null });
      }
    }
  },
}));
