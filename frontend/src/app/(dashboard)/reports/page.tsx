"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  FileText,
  FolderOpen,
  Search,
  Download,
  TrendingUp,
  Clock,
} from "lucide-react";
import api from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DashboardStats } from "@/types/api";

interface ReportData {
  storage: {
    total_files: number;
    total_size_bytes: number;
    by_type: Record<string, { count: number; size_bytes: number }>;
  };
  processing: {
    total_processed: number;
    success_rate: number;
    avg_time_ms: number;
    by_status: Record<string, number>;
  };
  activity: {
    daily_uploads: { date: string; count: number }[];
    top_tags: { tag: string; count: number }[];
    recent_reports: {
      id: string;
      name: string;
      type: string;
      generated_at: string;
      file_size: number;
    }[];
  };
}

export default function ReportsPage() {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: async () => {
      const res = await api.get("/dashboard/stats");
      return res.data;
    },
  });

  const { data: reportData, isLoading: reportLoading } = useQuery<ReportData>({
    queryKey: ["reports", "summary"],
    queryFn: async () => {
      const res = await api.get("/reports/summary");
      return res.data;
    },
  });

  const isLoading = statsLoading || reportLoading;

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reports</h1>
          <p className="text-muted-foreground">
            Analytics and insights for your archive
          </p>
        </div>
        <Button>
          <Download className="mr-2 h-4 w-4" />
          Export Report
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>Total Files</CardDescription>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_files ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {formatBytes(stats?.storage_used_bytes ?? 0)} total
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>Documents</CardDescription>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_documents ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              Processed and indexed
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>Searches</CardDescription>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_searches ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              Total queries performed
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>Avg Processing</CardDescription>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((stats?.avg_processing_time_ms ?? 0) / 1000).toFixed(1)}s
            </div>
            <p className="text-xs text-muted-foreground">
              Per document
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <BarChart3 className="h-5 w-5" />
              Files by Type
            </CardTitle>
            <CardDescription>Distribution of file types in your archive</CardDescription>
          </CardHeader>
          <CardContent>
            {reportData?.storage.by_type ? (
              <div className="space-y-3">
                {Object.entries(reportData.storage.by_type)
                  .sort(([, a], [, b]) => b.count - a.count)
                  .slice(0, 8)
                  .map(([type, data]) => {
                    const maxCount = Math.max(
                      ...Object.values(reportData.storage.by_type).map((d) => d.count)
                    );
                    const percentage = (data.count / maxCount) * 100;
                    return (
                      <div key={type} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">{type}</span>
                          <span className="text-muted-foreground">
                            {data.count} files ({formatBytes(data.size_bytes)})
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary/70 transition-all"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No data available
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="h-5 w-5" />
              Processing Status
            </CardTitle>
            <CardDescription>Document processing pipeline health</CardDescription>
          </CardHeader>
          <CardContent>
            {reportData?.processing.by_status ? (
              <div className="space-y-3">
                {Object.entries(reportData.processing.by_status).map(([status, count]) => {
                  const total = Object.values(reportData.processing.by_status).reduce(
                    (a, b) => a + b,
                    0
                  );
                  const percentage = total > 0 ? (count / total) * 100 : 0;
                  const variant =
                    status === "completed"
                      ? "success"
                      : status === "failed"
                      ? "destructive"
                      : "secondary";
                  return (
                    <div key={status} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <Badge variant={variant} className="capitalize">
                          {status}
                        </Badge>
                        <span className="text-muted-foreground">
                          {count} ({percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            status === "completed"
                              ? "bg-emerald-500"
                              : status === "failed"
                              ? "bg-red-500"
                              : "bg-muted-foreground/30"
                          } transition-all`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No processing data available
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Top Tags</CardTitle>
          <CardDescription>Most frequently used tags across your documents</CardDescription>
        </CardHeader>
        <CardContent>
          {reportData?.activity.top_tags && reportData.activity.top_tags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {reportData.activity.top_tags.map((tag) => (
                <Badge key={tag.tag} variant="secondary" className="text-sm">
                  {tag.tag}
                  <span className="ml-1 text-muted-foreground">({tag.count})</span>
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No tags found
            </p>
          )}
        </CardContent>
      </Card>

      {reportData?.activity.recent_reports &&
        reportData.activity.recent_reports.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Generated Reports</CardTitle>
              <CardDescription>Previously generated report files</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {reportData.activity.recent_reports.map((report) => (
                  <div
                    key={report.id}
                    className="flex items-center justify-between rounded-md border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">{report.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {report.type} &middot; {formatDateTime(report.generated_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {formatBytes(report.file_size)}
                      </span>
                      <Button variant="ghost" size="sm">
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
    </div>
  );
}
