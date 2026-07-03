"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type {
  User,
  AuthTokens,
  LoginRequest,
  RegisterRequest,
} from "@/types/api";

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
      // Fetch user after login
      api.get<User>("/auth/me").then(({ data: userData }) => {
        login(userData, tokens);
        router.push("/dashboard");
      });
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (data: RegisterRequest) => {
      const response = await api.post<AuthTokens>("/auth/register", data);
      return response.data;
    },
    onSuccess: (tokens) => {
      registerMutation.reset();
      api.get<User>("/auth/me").then(({ data: userData }) => {
        login(userData, tokens);
        router.push("/dashboard");
      });
    },
  });

  const { data: currentUser } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const response = await api.get<User>("/auth/me");
      return response.data;
    },
    enabled: isAuthenticated && !user,
    retry: false,
    onSuccess: (data) => {
      setUser(data);
    },
  });

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return {
    user: user ?? currentUser,
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
