import { create } from "zustand";

interface ConfigState {
  serverUrl: string;
  apiKey: string;
  agentName: string;
  folders: string[];
  setConfig: (config: Partial<ConfigState>) => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  serverUrl: localStorage.getItem("serverUrl") || "http://localhost:8000",
  apiKey: localStorage.getItem("apiKey") || "",
  agentName: localStorage.getItem("agentName") || "",
  folders: JSON.parse(localStorage.getItem("folders") || "[]"),
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
}));
