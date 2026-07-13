"use client";

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface WorkflowStatsGridProps {
  stats: { total: number; active: number; completed: number; failed: number };
  t: (key: string) => string;
}

export default function WorkflowStatsGrid({ stats, t }: WorkflowStatsGridProps) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("totalWorkflows")}</CardDescription>
          <CardTitle className="text-2xl">{stats.total}</CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("active")}</CardDescription>
          <CardTitle className="text-2xl text-brand-teal">
            {stats.active}
          </CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("completed")}</CardDescription>
          <CardTitle className="text-2xl text-brand-cyan">
            {stats.completed}
          </CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("failed")}</CardDescription>
          <CardTitle className="text-2xl text-red-600">
            {stats.failed}
          </CardTitle>
        </CardHeader>
      </Card>
    </div>
  );
}
