import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createCookieStorage } from "@/lib/cookie-storage";
import type { User, AuthTokens } from "@/types/api";

function setCookie(name: string, value: string, days: number = 7) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function removeCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  login: (tokens: AuthTokens) => void;
  logout: () => void;
  switchOrganization: (tokens: { access: string; refresh: string }, user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setUser: (user) => set({ user }),

      setTokens: (accessToken, refreshToken) => {
        setCookie("accessToken", accessToken);
        setCookie("refreshToken", refreshToken);
        set({ accessToken, refreshToken });
      },

      login: (tokens) => {
        setCookie("accessToken", tokens.access);
        setCookie("refreshToken", tokens.refresh);
        set({
          user: tokens.user,
          accessToken: tokens.access,
          refreshToken: tokens.refresh,
          isAuthenticated: true,
        });
      },

      logout: () => {
        removeCookie("accessToken");
        removeCookie("refreshToken");
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      switchOrganization: (tokens, user) => {
        setCookie("accessToken", tokens.access);
        setCookie("refreshToken", tokens.refresh);
        set({
          user,
          accessToken: tokens.access,
          refreshToken: tokens.refresh,
        });
      },
    }),
    {
      name: "auth-storage",
      storage: createCookieStorage(),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
