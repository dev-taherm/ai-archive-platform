"use client";

import { useTranslations } from "next-intl";
import { Clock, Loader2, CheckCircle, XCircle, ChevronRight, Settings } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WorkflowStep } from "@/types/api";
import { stepStatusIconName } from "@/lib/constants";

const iconMap: Record<string, typeof Clock> = { Clock, Loader2, CheckCircle, XCircle };
const stepStatusIcon = Object.fromEntries(
  Object.entries(stepStatusIconName).map(([k, v]) => [k, iconMap[v]])
) as Record<string, typeof Clock>;

type Translator = ReturnType<typeof useTranslations>;

interface WorkflowStepVisualizationProps {
  steps: WorkflowStep[];
  t: Translator;
}

const statusColors: Record<string, string> = {
  completed: "text-brand-teal",
  failed: "text-red-500",
  running: "text-brand-cyan animate-spin",
};

const badgeVariants: Record<string, "success" | "destructive" | "warning" | "secondary"> = {
  completed: "success",
  failed: "destructive",
  running: "warning",
};

export default function WorkflowStepVisualization({ steps, t }: WorkflowStepVisualizationProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Settings className="h-4 w-4 text-brand-teal" />
          {t("pipelineSteps", { count: steps.length })}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {steps.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            {t("noStepsConfigured")}
          </p>
        ) : (
          <div className="space-y-2">
            {steps.map((step, i) => {
              const StepIcon = stepStatusIcon[step.status] || Clock;
              return (
                <div
                  key={step.id}
                  className="flex items-center gap-3 p-3 rounded-lg border"
                >
                  <span className="text-xs text-muted-foreground w-6">
                    #{i + 1}
                  </span>
                  <div className="flex items-center gap-2 flex-1">
                    <StepIcon
                      className={`h-4 w-4 ${statusColors[step.status] || "text-muted-foreground"}`}
                    />
                    <div>
                      <p className="text-sm font-medium">{step.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {step.type}
                      </p>
                    </div>
                  </div>
                  <Badge variant={badgeVariants[step.status] || "secondary"}>
                    {step.status}
                  </Badge>
                  {i < steps.length - 1 && (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
