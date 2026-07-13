"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  GitBranch,
  Play,
  Pause,
  Trash2,
  Clock,
  ChevronRight,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Workflow } from "@/types/api";
import { workflowStatusVariant as statusVariant, stepStatusIconName } from "@/lib/constants";

const iconMap: Record<string, typeof Clock> = { Clock, Loader2, CheckCircle, XCircle };
const stepStatusIcon = Object.fromEntries(
  Object.entries(stepStatusIconName).map(([k, v]) => [k, iconMap[v]])
) as Record<string, typeof Clock>;

type Translator = ReturnType<typeof useTranslations>;

interface WorkflowListProps {
  workflows: Workflow[];
  isLoading: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  expandedId: string | null;
  onToggleExpand: (id: string) => void;
  onRun: (id: string) => void;
  onPause: (id: string) => void;
  onDelete: (id: string) => void;
  running: Record<string, boolean>;
  t: Translator;
  tc: Translator;
}

export default function WorkflowList({
  workflows,
  isLoading,
  search,
  onSearchChange,
  expandedId,
  onToggleExpand,
  onRun,
  onPause,
  onDelete,
  running,
  t,
  tc,
}: WorkflowListProps) {
  const filtered = workflows.filter(
    (w) =>
      w.name.toLowerCase().includes(search.toLowerCase()) ||
      w.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Input
            placeholder={t("searchPlaceholder")}
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="max-w-sm"
          />
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8 text-muted-foreground">
            {t("loading")}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <GitBranch className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
            <p className="text-lg font-medium">{t("noWorkflows")}</p>
            <p className="text-sm">
              {search ? tc("tryDifferentSearch") : t("noWorkflowsDesc")}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((workflow) => (
              <div
                key={workflow.id}
                className="rounded-lg border transition-colors hover:bg-muted/50"
              >
                <div
                  className="flex items-center justify-between p-4 cursor-pointer"
                  onClick={() => onToggleExpand(workflow.id)}
                >
                  <div className="flex items-center gap-3">
                    <GitBranch className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <Link
                        href={`/workflows/${workflow.id}`}
                        className="font-medium hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {workflow.name}
                      </Link>
                      <p className="text-sm text-muted-foreground">
                        {workflow.description || tc("noDescription")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={statusVariant[workflow.status] || "secondary"}>
                      {workflow.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {t("runs", { n: workflow.run_count })}
                    </span>
                    <ChevronRight
                      className={`h-4 w-4 transition-transform ${
                        expandedId === workflow.id ? "rotate-90" : ""
                      }`}
                    />
                  </div>
                </div>

                {expandedId === workflow.id && (
                  <div className="border-t p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">
                          {t("trigger")}
                        </span>
                        <Badge variant="outline">{workflow.trigger}</Badge>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {t("lastRun")}
                        </span>
                        {workflow.last_run_at
                          ? formatDateTime(workflow.last_run_at)
                          : tc("never")}
                      </div>
                    </div>

                    {workflow.steps.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">{t("steps")}</p>
                        <div className="flex items-center gap-2 flex-wrap">
                          {workflow.steps.map((step, i) => {
                            const StepIcon =
                              stepStatusIcon[step.status] || Clock;
                            return (
                              <div
                                key={step.id}
                                className="flex items-center gap-1"
                              >
                                {i > 0 && (
                                  <ChevronRight className="h-3 w-3 text-muted-foreground" />
                                )}
                                <Badge variant="outline" className="gap-1">
                                  <StepIcon className="h-3 w-3" />
                                  {step.name}
                                </Badge>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    <div className="flex gap-2">
                      {workflow.status === "active" ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onPause(workflow.id)}
                          disabled={running[workflow.id]}
                        >
                          <Pause className="mr-1 h-3.5 w-3.5" />
                          {t("pause")}
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => onRun(workflow.id)}
                          disabled={
                            running[workflow.id] ||
                            workflow.status === "completed"
                          }
                        >
                          <Play className="mr-1 h-3.5 w-3.5" />
                          {t("run")}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => onDelete(workflow.id)}
                      >
                        <Trash2 className="mr-1 h-3.5 w-3.5" />
                        {tc("delete")}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
