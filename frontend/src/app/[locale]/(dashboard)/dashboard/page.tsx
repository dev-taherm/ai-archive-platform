"use client";

import { useTranslations } from "next-intl";
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
import ScopeSelector from "@/components/features/shared/scope-selector";
import { useState } from "react";
import type { DashboardStats, ActivityResponse } from "@/types/api";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const [scope, setScope] = useState<"personal" | "organization">("personal");
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats", scope],
    queryFn: async () => {
      const response = await api.get("/dashboard/stats", { params: { scope } });
      return response.data;
    },
  });

  const { data: activityData } = useQuery<ActivityResponse>({
    queryKey: ["dashboard", "activity", scope],
    queryFn: async () => {
      const response = await api.get("/dashboard/activity", { params: { scope } });
      return response.data;
    },
  });

  if (statsLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-cyan border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
        <p className="text-muted-foreground">
          {t("subtitle")}
        </p>
      </div>

      <ScopeSelector value={scope} onChange={setScope} className="mb-4" />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title={t("totalFiles")}
          value={stats?.total_files ?? 0}
          icon={FolderOpen}
        />
        <StatsCard
          title={t("totalDocuments")}
          value={stats?.total_documents ?? 0}
          icon={FileText}
        />
        <StatsCard
          title={t("storageUsed")}
          value={formatBytes(stats?.storage_used_bytes ?? 0)}
          icon={HardDrive}
        />
        <StatsCard
          title={t("failedProcessing")}
          value={
            (stats?.files_by_status?.failed ?? 0) +
            (stats?.documents_by_status?.failed ?? 0)
          }
          icon={AlertCircle}
          description={t("failedProcessingDesc")}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title={t("agentsOnline")}
          value={`${stats?.agents_online ?? 0} / ${stats?.agents_total ?? 0}`}
          icon={Bot}
          description={t("agentsOnlineDesc")}
        />
        <StatsCard
          title={t("duplicateFiles")}
          value={stats?.duplicate_files ?? 0}
          icon={Copy}
          description={t("acrossGroups", { count: stats?.duplicate_groups ?? 0 })}
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
