import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  serverUrl: string;
  webUrl: string;
  configLoaded: boolean;
  login: (serverUrl: string, token: string) => void;
  logout: () => void;
  loadServerConfig: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: !!localStorage.getItem("token"),
  token: localStorage.getItem("token"),
  serverUrl: localStorage.getItem("serverUrl") || "",
  webUrl: "",
  configLoaded: false,
  login: (serverUrl, token) => {
    localStorage.setItem("token", token);
    localStorage.setItem("serverUrl", serverUrl);
    set({ isAuthenticated: true, token, serverUrl });
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("serverUrl");
    set({ isAuthenticated: false, token: null });
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
  },
}));
