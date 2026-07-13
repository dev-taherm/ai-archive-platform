"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface WorkspaceStatsProps {
  docCount: number;
  summaryCount: number;
  entityCount: number;
  typeCount: number;
  t: Function;
}

export default function WorkspaceStats({
  docCount,
  summaryCount,
  entityCount,
  typeCount,
  t,
}: WorkspaceStatsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("documentsAnalyzed")}</CardDescription>
          <CardTitle className="text-2xl">{docCount}</CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("withSummaries")}</CardDescription>
          <CardTitle className="text-2xl text-brand-teal">{summaryCount}</CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("uniqueEntities")}</CardDescription>
          <CardTitle className="text-2xl text-brand-cyan">{entityCount}</CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("classificationTypes")}</CardDescription>
          <CardTitle className="text-2xl text-brand-teal">{typeCount}</CardTitle>
        </CardHeader>
      </Card>
    </div>
  );
}
