"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
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
import type { DashboardStats, ReportData } from "@/types/api";

export default function ReportsPage() {
  const t = useTranslations("reports");
  const tc = useTranslations("common");
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
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-cyan border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t('title')}</h1>
          <p className="text-muted-foreground">
            {t('subtitle')}
          </p>
        </div>
        <Button>
          <Download className="mr-2 h-4 w-4" />
          {t('exportReport')}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>{t('totalFiles')}</CardDescription>
            <div className="rounded-md bg-brand-teal/10 p-1.5">
              <FolderOpen className="h-4 w-4 text-brand-teal" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_files ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {t('totalSize', { size: formatBytes(stats?.storage_used_bytes ?? 0) })}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>{t('documents')}</CardDescription>
            <div className="rounded-md bg-brand-teal/10 p-1.5">
              <FileText className="h-4 w-4 text-brand-teal" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_documents ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {t('processedAndIndexed')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>{t('searches')}</CardDescription>
            <div className="rounded-md bg-brand-cyan/10 p-1.5">
              <Search className="h-4 w-4 text-brand-cyan" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_searches ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {t('totalQueries')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardDescription>{t('avgProcessing')}</CardDescription>
            <div className="rounded-md bg-brand-cyan/10 p-1.5">
              <Clock className="h-4 w-4 text-brand-cyan" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((stats?.avg_processing_time_ms ?? 0) / 1000).toFixed(1)}s
            </div>
            <p className="text-xs text-muted-foreground">
              {t('perDocument')}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <BarChart3 className="h-5 w-5 text-brand-teal" />
              {t('filesByType')}
            </CardTitle>
            <CardDescription>{t('filesByTypeDesc')}</CardDescription>
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
                            {t('fileTypeCount', { count: data.count, size: formatBytes(data.size_bytes) })}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-brand-teal to-brand-cyan transition-all"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                {tc('noData')}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="h-5 w-5 text-brand-cyan" />
              {t('processingStatus')}
            </CardTitle>
            <CardDescription>{t('processingStatusDesc')}</CardDescription>
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
                                ? "bg-brand-teal"
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
                {t('noProcessingData')}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('topTags')}</CardTitle>
          <CardDescription>{t('topTagsDesc')}</CardDescription>
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
              {t('noTags')}
            </p>
          )}
        </CardContent>
      </Card>

      {reportData?.activity.recent_reports &&
        reportData.activity.recent_reports.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{t('generatedReports')}</CardTitle>
              <CardDescription>{t('generatedReportsDesc')}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {reportData.activity.recent_reports.map((report) => (
                  <div
                    key={report.id}
                    className="flex items-center justify-between rounded-md border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-4 w-4 text-brand-teal" />
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
