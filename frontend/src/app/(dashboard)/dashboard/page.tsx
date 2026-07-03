"use client";

import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  HardDrive,
  Search,
  AlertCircle,
} from "lucide-react";
import api from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import { StatsCard } from "@/components/features/dashboard/stats-card";
import { RecentActivity } from "@/components/features/dashboard/recent-activity";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DashboardStats } from "@/types/api";

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: async () => {
      const response = await api.get("/dashboard/stats");
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your archive platform
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Documents"
          value={stats?.total_documents ?? 0}
          icon={FileText}
          trend={{ value: 12, isPositive: true }}
        />
        <StatsCard
          title="Storage Used"
          value={formatBytes(stats?.storage_used_bytes ?? 0)}
          icon={HardDrive}
        />
        <StatsCard
          title="Total Searches"
          value={stats?.total_searches ?? 0}
          icon={Search}
          trend={{ value: 8, isPositive: true }}
        />
        <StatsCard
          title="Failed Processing"
          value={stats?.documents_by_status.failed ?? 0}
          icon={AlertCircle}
          description="Documents requiring attention"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-7">
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle>Activity Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats?.activity_over_time ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="uploads" fill="hsl(222.2, 47.4%, 11.2%)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="searches" fill="hsl(210, 40%, 96.1%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
        <div className="lg:col-span-3">
          <RecentActivity activities={stats?.recent_activity ?? []} />
        </div>
      </div>
    </div>
  );
}
