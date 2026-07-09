"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type {
  Organization,
  Membership,
  Invitation,
  SwitchOrgResponse,
} from "@/types/api";

// --- Organization ---

export function useOrganization() {
  return useQuery({
    queryKey: ["organization", "current"],
    queryFn: async () => {
      const response = await api.get<Organization>("/organizations/current/");
      return response.data;
    },
  });
}

export function useOrganizations() {
  return useQuery({
    queryKey: ["organizations"],
    queryFn: async () => {
      const response = await api.get<{ results: Organization[] }>("/organizations/");
      return response.data.results;
    },
  });
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Pick<Organization, "name" | "description">>) => {
      const response = await api.patch<Organization>("/organizations/current/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization"] });
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

// --- Switch Organization ---

export function useSwitchOrganization() {
  const queryClient = useQueryClient();
  const { switchOrganization } = useAuthStore.getState();
  return useMutation({
    mutationFn: async (organizationId: string) => {
      const response = await api.post<SwitchOrgResponse>("/organizations/switch/", {
        organization_id: organizationId,
      });
      return response.data;
    },
    onSuccess: async (data) => {
      // Update tokens and refetch user
      switchOrganization(
        { access: data.access, refresh: data.refresh },
        { ...useAuthStore.getState().user!, current_organization: data.organization.id }
      );
      // Refetch user data from server
      try {
        const userRes = await api.get("/users/me/");
        useAuthStore.getState().setUser(userRes.data);
      } catch {}
      queryClient.invalidateQueries({ queryKey: ["organization"] });
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

// --- Leave Organization ---

export function useLeaveOrganization() {
  const queryClient = useQueryClient();
  const { switchOrganization } = useAuthStore.getState();
  return useMutation({
    mutationFn: async () => {
      const response = await api.post("/organizations/leave/");
      return response.data;
    },
    onSuccess: async () => {
      // Refetch user data from server
      try {
        const userRes = await api.get("/users/me/");
        useAuthStore.getState().setUser(userRes.data);
      } catch {}
      queryClient.invalidateQueries({ queryKey: ["organization"] });
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

// --- Memberships ---

export function useOrgMembers() {
  return useQuery({
    queryKey: ["organization", "members"],
    queryFn: async () => {
      const response = await api.get<{ results: Membership[] }>("/memberships/");
      return response.data.results;
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (membershipId: string) => {
      await api.delete(`/memberships/${membershipId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization", "members"] });
    },
  });
}

// --- Invitations ---

export function useOrgInvitations() {
  return useQuery({
    queryKey: ["organization", "invitations"],
    queryFn: async () => {
      const response = await api.get<{ results: Invitation[] }>("/invitations/");
      return response.data.results;
    },
  });
}

export function useInviteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { email: string; role: string }) => {
      const response = await api.post<Invitation>("/invitations/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization", "invitations"] });
    },
  });
}

export function useRevokeInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invitationId: string) => {
      await api.delete(`/invitations/${invitationId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization", "invitations"] });
    },
  });
}

// --- Create Organization ---

export function useCreateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; slug: string; description?: string }) => {
      const response = await api.post<Organization>("/organizations/create_organization/", data);
      return response.data;
    },
    onSuccess: async () => {
      // Refetch user to get updated org
      try {
        const userRes = await api.get("/users/me/");
        useAuthStore.getState().setUser(userRes.data);
      } catch {}
      queryClient.invalidateQueries({ queryKey: ["organization"] });
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}
