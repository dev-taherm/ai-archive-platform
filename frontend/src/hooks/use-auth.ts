"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { User, AuthTokens, LoginRequest, RegisterRequest } from "@/types/api";

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, login, logout, setUser } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: async (data: LoginRequest) => {
      const response = await api.post<AuthTokens>("/auth/login", data);
      return response.data;
    },
    onSuccess: (tokens) => {
      loginMutation.reset();
      login(tokens);
      router.push("/dashboard");
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (data: RegisterRequest) => {
      const response = await api.post<AuthTokens>("/auth/register", data);
      return response.data;
    },
    onSuccess: (tokens) => {
      registerMutation.reset();
      login(tokens);
      router.push("/dashboard");
    },
  });

  // Rehydrate user from persisted store by calling /users/me
  const { data: currentUser } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const response = await api.get<User>("/users/me");
      return response.data;
    },
    enabled: isAuthenticated && !user,
    retry: false,
  });

  // Sync currentUser back to store
  useEffect(() => {
    if (currentUser && !user) {
      setUser(currentUser);
    }
  }, [currentUser, user, setUser]);

  const handleLogout = async () => {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh: refreshToken });
      } catch {
        // Token may already be invalid — proceed with local logout
      }
    }
    logout();
    router.push("/login");
  };

  return {
    user: (user ?? currentUser) as User | null,
    isAuthenticated,
    login: loginMutation.mutate,
    register: registerMutation.mutate,
    logout: handleLogout,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
    loginError: loginMutation.error,
    registerError: registerMutation.error,
  };
}
