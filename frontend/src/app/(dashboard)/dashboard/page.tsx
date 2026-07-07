"use client";

import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  HardDrive,
  AlertCircle,
  FolderOpen,
  Bot,
  Copy,
} from "lucide-react";
import api from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import { StatsCard } from "@/components/features/dashboard/stats-card";
import { RecentActivity } from "@/components/features/dashboard/recent-activity";
import Recommendations from "@/components/features/dashboard/recommendations";
import {
  FileTypeChart,
  FileStatusChart,
} from "@/components/features/dashboard/charts-section";
import type { DashboardStats, ActivityResponse } from "@/types/api";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: async () => {
      const response = await api.get("/dashboard/stats");
      return response.data;
    },
  });

  const { data: activityData } = useQuery<ActivityResponse>({
    queryKey: ["dashboard", "activity"],
    queryFn: async () => {
      const response = await api.get("/dashboard/activity");
      return response.data;
    },
  });

  if (statsLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your archive platform
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Files"
          value={stats?.total_files ?? 0}
          icon={FolderOpen}
        />
        <StatsCard
          title="Total Documents"
          value={stats?.total_documents ?? 0}
          icon={FileText}
        />
        <StatsCard
          title="Storage Used"
          value={formatBytes(stats?.storage_used_bytes ?? 0)}
          icon={HardDrive}
        />
        <StatsCard
          title="Failed Processing"
          value={
            (stats?.files_by_status?.failed ?? 0) +
            (stats?.documents_by_status?.failed ?? 0)
          }
          icon={AlertCircle}
          description="Files or documents requiring attention"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Agents Online"
          value={`${stats?.agents_online ?? 0} / ${stats?.agents_total ?? 0}`}
          icon={Bot}
          description="Connected edge agents"
        />
        <StatsCard
          title="Duplicate Files"
          value={stats?.duplicate_files ?? 0}
          icon={Copy}
          description={`Across ${stats?.duplicate_groups ?? 0} groups`}
        />
      </div>

      <Recommendations />

      <div className="grid gap-6 md:grid-cols-2">
        <FileTypeChart
          data={Object.entries(stats?.documents_by_type ?? {}).map(
            ([name, value]) => ({ name, value })
          )}
        />
        <FileStatusChart
          data={Object.entries(stats?.files_by_status ?? {}).map(
            ([name, value]) => ({ name, value })
          )}
        />
      </div>

      <RecentActivity activities={activityData?.activities ?? []} />
    </div>
  );
}
