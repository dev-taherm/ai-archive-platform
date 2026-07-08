"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  Organization,
  Membership,
  Invitation,
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

export function useUpdateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Pick<Organization, "name" | "description">>) => {
      const response = await api.patch<Organization>("/organizations/current/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization"] });
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization"] });
    },
  });
}
