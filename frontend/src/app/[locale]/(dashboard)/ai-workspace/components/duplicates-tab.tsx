"use client";

import Link from "next/link";
import { Copy, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DashboardStats } from "@/types/api";

interface DuplicatesTabProps {
  stats: DashboardStats | undefined;
  t: Function;
  tc: Function;
}

export default function DuplicatesTab({ stats, t, tc }: DuplicatesTabProps) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("duplicateDetection")}</CardTitle>
          <CardDescription>{t("duplicateDetectionDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          {stats ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">{t("duplicateFiles")}</p>
                <p className="text-3xl font-bold text-brand-teal">{stats.duplicate_files}</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">Duplicate Groups</p>
                <p className="text-3xl font-bold text-brand-cyan">{stats.duplicate_groups}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("loadingStats")}</p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Copy className="mb-4 h-12 w-12 text-brand-cyan opacity-50" />
          <p className="text-lg font-medium">{t("duplicateGroupDetails")}</p>
          <p className="text-sm text-muted-foreground text-center max-w-md">
            {t("duplicateGroupDesc")}
          </p>
          <Link href="/dashboard">
            <Button variant="brand" className="mt-4"><BarChart3 className="mr-2 h-4 w-4" /> {tc("goToDashboard")}</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
