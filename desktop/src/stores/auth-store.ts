import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

interface AgentInfo {
  agent_id: string;
  api_key: string;
}

export interface UserInfo {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  organization_name: string;
}

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  refreshToken: string | null;
  serverUrl: string;
  webUrl: string;
  configLoaded: boolean;
  agent: AgentInfo | null;
  user: UserInfo | null;
  login: (serverUrl: string, token: string, refreshToken?: string) => void;
  logout: () => void;
  setAgent: (agent: AgentInfo) => void;
  fetchUser: () => Promise<void>;
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
  user: (() => {
    try { return JSON.parse(localStorage.getItem("user") || "null"); } catch { return null; }
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
    localStorage.removeItem("user");
    set({ isAuthenticated: false, token: null, refreshToken: null, agent: null, user: null });
  },
  setAgent: (agent) => {
    localStorage.setItem("agent", JSON.stringify(agent));
    set({ agent });
  },
  fetchUser: async () => {
    const { serverUrl, token } = get();
    if (!serverUrl || !token) return;
    try {
      const data = await invoke<{
        id?: string;
        email?: string;
        username?: string;
        first_name?: string;
        last_name?: string;
        organization_name?: string;
      }>("fetch_user_profile", { serverUrl, accessToken: token });
      const user: UserInfo = {
        id: data.id || "",
        email: data.email || "",
        username: data.username || "",
        first_name: data.first_name || "",
        last_name: data.last_name || "",
        organization_name: data.organization_name || "",
      };
      localStorage.setItem("user", JSON.stringify(user));
      set({ user });
    } catch (e) {
      console.warn("Failed to fetch user profile:", e);
    }
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
        localStorage.removeItem("user");
        set({ isAuthenticated: false, token: null, refreshToken: null, serverUrl: "", agent: null, user: null });
      }
    }
    // Fetch user profile if authenticated but not yet loaded
    if (isAuthenticated && serverUrl && token && !get().user) {
      get().fetchUser();
    }
  },
}));
