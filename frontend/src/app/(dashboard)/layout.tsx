"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "@/components/ui/sidebar";
import { Header } from "@/components/ui/header";
import { useUIStore } from "@/stores/ui-store";
import { useAuthStore } from "@/stores/auth-store";
import { OnboardingModal } from "@/components/features/onboarding/setup-device-modal";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { sidebarOpen } = useUIStore();
  const { user } = useAuthStore();
  const [showOnboarding, setShowOnboarding] = useState(false);

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
          sidebarOpen ? "ml-64" : "ml-16"
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
