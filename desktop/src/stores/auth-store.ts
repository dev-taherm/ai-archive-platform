import { create } from "zustand";

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  serverUrl: string;
  login: (serverUrl: string, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!localStorage.getItem("token"),
  token: localStorage.getItem("token"),
  serverUrl: localStorage.getItem("serverUrl") || "http://localhost:8000",
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
}));
