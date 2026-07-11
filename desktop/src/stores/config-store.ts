import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";

interface ConfigState {
  serverUrl: string;
  apiKey: string;
  agentName: string;
  folders: string[];
  configLoaded: boolean;
  setConfig: (config: Partial<ConfigState>) => void;
  loadConfig: () => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  serverUrl: localStorage.getItem("serverUrl") || "",
  apiKey: localStorage.getItem("apiKey") || "",
  agentName: localStorage.getItem("agentName") || "",
  folders: JSON.parse(localStorage.getItem("folders") || "[]"),
  configLoaded: false,
  setConfig: (config) => {
    set((state) => {
      const next = { ...state, ...config };
      localStorage.setItem("serverUrl", next.serverUrl);
      localStorage.setItem("apiKey", next.apiKey);
      localStorage.setItem("agentName", next.agentName);
      localStorage.setItem("folders", JSON.stringify(next.folders));
      return next;
    });
  },
  loadConfig: async () => {
    if (get().configLoaded) return;
    try {
      const config = await invoke<Record<string, string>>("get_config");
      if (config.server_url && !get().serverUrl) {
        set({ serverUrl: config.server_url, configLoaded: true });
      } else {
        set({ configLoaded: true });
      }
    } catch {
      set({ configLoaded: true });
    }
  },
}));
