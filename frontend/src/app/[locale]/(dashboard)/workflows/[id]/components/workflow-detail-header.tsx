"use client";

import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  Play,
  Pause,
  Trash2,
  RefreshCw,
  GitBranch,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Workflow } from "@/types/api";
import { workflowStatusVariant as statusVariant } from "@/lib/constants";

type Translator = ReturnType<typeof useTranslations>;

interface WorkflowDetailHeaderProps {
  workflow: Workflow;
  onBack: () => void;
  onRefresh: () => void;
  onRun: () => void;
  onPause: () => void;
  onDelete: () => void;
  isRunning: boolean;
  isPausing: boolean;
  t: Translator;
  tc: Translator;
}

export default function WorkflowDetailHeader({
  workflow,
  onBack,
  onRefresh,
  onRun,
  onPause,
  onDelete,
  isRunning,
  isPausing,
  t,
  tc,
}: WorkflowDetailHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-muted p-2">
            <GitBranch className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">
              {workflow.name}
            </h1>
            <p className="text-sm text-muted-foreground">
              {workflow.description || tc("noDescription")}
            </p>
          </div>
        </div>
        <Badge variant={statusVariant[workflow.status] || "secondary"}>
          {workflow.status}
        </Badge>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          {t("refresh")}
        </Button>
        {workflow.status === "active" ? (
          <Button
            variant="outline"
            size="sm"
            onClick={onPause}
            disabled={isPausing}
          >
            <Pause className="h-4 w-4 mr-2" />
            {t("pause")}
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={onRun}
            disabled={isRunning || workflow.status === "completed"}
          >
            <Play className="h-4 w-4 mr-2" />
            {t("run")}
          </Button>
        )}
        <Button variant="destructive" size="sm" onClick={onDelete}>
          <Trash2 className="h-4 w-4 mr-2" />
          {tc("delete")}
        </Button>
      </div>
    </div>
  );
}
