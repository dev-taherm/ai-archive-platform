"use client";

import { use, useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, XCircle, History, Clock, Settings } from "lucide-react";
import type { Workflow, WorkflowRun } from "@/types/api";
import WorkflowDetailHeader from "./components/workflow-detail-header";
import WorkflowRunHistory from "./components/workflow-run-history";
import WorkflowStepVisualization from "./components/workflow-step-visualization";

export default function WorkflowDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const t = useTranslations("workflows");
  const tc = useTranslations("common");
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const { data: workflow, isLoading } = useQuery<Workflow>({
    queryKey: ["workflows", id],
    queryFn: async () => (await api.get(`/workflows/${id}`)).data,
  });

  const { data: runsData } = useQuery<{ workflow_id: string; run_count: number; runs: WorkflowRun[] }>({
    queryKey: ["workflows", id, "runs"],
    queryFn: async () => (await api.get(`/workflows/${id}/runs`, { params: { limit: 50 } })).data,
    enabled: !!workflow,
  });

  const runs = runsData?.runs || [];

  const runMutation = useMutation({
    mutationFn: async () => api.post(`/workflows/${id}/run`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows", id] });
      queryClient.invalidateQueries({ queryKey: ["workflows", id, "runs"] });
      toast({ title: t("workflowStarted") });
    },
    onError: () => toast({ title: t("workflowStartFailed"), variant: "destructive" }),
  });

  const pauseMutation = useMutation({
    mutationFn: async () => api.post(`/workflows/${id}/pause`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows", id] });
      toast({ title: t("workflowPaused") });
    },
    onError: () => toast({ title: t("workflowPauseFailed"), variant: "destructive" }),
  });

  const deleteMutation = useMutation({
    mutationFn: async () => api.delete(`/workflows/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      toast({ title: t("workflowDeleted") });
      router.push("/workflows");
    },
    onError: () => toast({ title: t("workflowDeleteFailed"), variant: "destructive" }),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6 animate-pulse">
                <div className="h-4 w-32 rounded bg-muted mb-2" />
                <div className="h-8 w-24 rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <XCircle className="h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">{t("notFound")}</p>
        <Button variant="outline" onClick={() => router.push("/workflows")}>
          <ArrowLeft className="h-4 w-4 mr-2" />{t("backToWorkflows")}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <WorkflowDetailHeader
        workflow={workflow}
        onBack={() => router.push("/workflows")}
        onRefresh={() => queryClient.invalidateQueries({ queryKey: ["workflows", id] })}
        onRun={() => runMutation.mutate()}
        onPause={() => pauseMutation.mutate()}
        onDelete={() => setShowDeleteDialog(true)}
        isRunning={runMutation.isPending}
        isPausing={pauseMutation.isPending}
        t={t} tc={tc}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardContent className="p-4"><div className="flex items-center gap-3">
          <div className="rounded-md bg-muted p-2"><History className="h-4 w-4" /></div>
          <div><p className="text-xs text-muted-foreground">{t("totalRuns")}</p>
          <p className="text-2xl font-bold">{workflow.run_count}</p></div>
        </div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="flex items-center gap-3">
          <div className="rounded-md bg-muted p-2"><Clock className="h-4 w-4" /></div>
          <div><p className="text-xs text-muted-foreground">{t("lastRun")}</p>
          <p className="text-sm font-medium">{workflow.last_run_at ? formatDate(workflow.last_run_at) : tc("never")}</p></div>
        </div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="flex items-center gap-3">
          <div className="rounded-md bg-muted p-2"><Settings className="h-4 w-4" /></div>
          <div><p className="text-xs text-muted-foreground">{t("trigger")}</p>
          <Badge variant="outline">{workflow.trigger}</Badge></div>
        </div></CardContent></Card>
      </div>

      <WorkflowStepVisualization steps={workflow.steps} t={t} />
      <WorkflowRunHistory runs={runs} t={t} />

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteWorkflow")}</AlertDialogTitle>
            <AlertDialogDescription>{t("deleteWorkflowConfirm")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate()} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              {tc("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
