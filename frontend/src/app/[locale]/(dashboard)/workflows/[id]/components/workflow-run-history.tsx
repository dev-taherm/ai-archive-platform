"use client";

import { useTranslations } from "next-intl";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { History } from "lucide-react";
import type { WorkflowRun } from "@/types/api";
import { workflowStatusVariant as statusVariant } from "@/lib/constants";

type Translator = ReturnType<typeof useTranslations>;

interface WorkflowRunHistoryProps {
  runs: WorkflowRun[];
  t: Translator;
}

export default function WorkflowRunHistory({ runs, t }: WorkflowRunHistoryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <History className="h-4 w-4 text-brand-cyan" />
          {t("runHistory", { count: runs.length })}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {runs.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            {t("noRunsYet")}
          </p>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <div
                key={run.id}
                className="flex items-center justify-between p-3 rounded-lg border"
              >
                <div className="flex items-center gap-3">
                  <Badge variant={statusVariant[run.status] || "secondary"}>
                    {run.status}
                  </Badge>
                  <div>
                    <p className="text-sm font-medium">
                      {t("stepIndicator", {
                        n: run.current_step,
                        m: run.total_steps,
                      })}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t("started", { date: formatDate(run.started_at) })}
                      {run.completed_at &&
                        ` — ${t("completedDate", {
                          date: formatDate(run.completed_at),
                        })}`}
                    </p>
                  </div>
                </div>
                {run.error_message && (
                  <p className="text-xs text-destructive max-w-xs truncate">
                    {run.error_message}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
