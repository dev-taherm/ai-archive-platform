"use client";

import { useState, useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Sidebar } from "@/components/ui/sidebar";
import { Header } from "@/components/ui/header";
import { useUIStore } from "@/stores/ui-store";
import { useAuthStore } from "@/stores/auth-store";
import { OnboardingModal } from "@/components/features/onboarding/setup-device-modal";
import { useDashboardWS } from "@/hooks/use-dashboard-ws";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { sidebarOpen } = useUIStore();
  const { user } = useAuthStore();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const queryClient = useQueryClient();

  // Real-time dashboard updates via WebSocket
  const onAgentStatusChanged = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["agents"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
  }, [queryClient]);

  const onFilesSynced = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["files"] });
    queryClient.invalidateQueries({ queryKey: ["agents"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
  }, [queryClient]);

  const onDocumentUpdate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
  }, [queryClient]);

  const onProcessingUpdate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    queryClient.invalidateQueries({ queryKey: ["files"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
  }, [queryClient]);

  useDashboardWS({
    onAgentStatusChanged,
    onFilesSynced,
    onDocumentUpdate,
    onProcessingUpdate,
  });

  // Show onboarding for new users (joined within last 5 minutes) with no agents
  useEffect(() => {
    if (!user) return;
    const joinedAt = new Date(user.date_joined).getTime();
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000;
    if (now - joinedAt < fiveMinutes) {
      setShowOnboarding(true);
    }
  }, [user]);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div
        className={cn(
          "transition-all duration-300",
          sidebarOpen ? "ms-64" : "ms-16"
        )}
      >
        <Header />
        <main className="p-6">{children}</main>
      </div>
      <OnboardingModal
        open={showOnboarding}
        onClose={() => setShowOnboarding(false)}
      />
    </div>
  );
}
