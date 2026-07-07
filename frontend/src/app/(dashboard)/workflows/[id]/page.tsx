"use client";

import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import {
  ArrowLeft,
  Play,
  Pause,
  Trash2,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronRight,
  GitBranch,
  History,
  Settings,
} from "lucide-react";
import { useState } from "react";

interface WorkflowStep {
  id: string;
  name: string;
  type: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: "draft" | "active" | "paused" | "completed" | "failed";
  trigger: string;
  steps: WorkflowStep[];
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  created_at: string;
  updated_at: string;
}

interface WorkflowRun {
  id: string;
  workflow_id: string;
  status: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  current_step: number;
  total_steps: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning"> = {
  draft: "secondary",
  active: "success",
  paused: "warning",
  completed: "success",
  failed: "destructive",
  running: "warning",
  succeeded: "success",
};

const stepStatusIcon: Record<string, typeof Clock> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle,
  failed: XCircle,
  skipped: Clock,
};

export default function WorkflowDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const { data: workflow, isLoading } = useQuery<Workflow>({
    queryKey: ["workflows", id],
    queryFn: async () => {
      const res = await api.get(`/workflows/${id}`);
      return res.data;
    },
  });

  const { data: runsData } = useQuery<{ workflow_id: string; run_count: number; runs: WorkflowRun[] }>({
    queryKey: ["workflows", id, "runs"],
    queryFn: async () => {
      const res = await api.get(`/workflows/${id}/runs`, { params: { limit: 50 } });
      return res.data;
    },
    enabled: !!workflow,
  });

  const runs = runsData?.runs || [];

  const runMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/workflows/${id}/run`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows", id] });
      queryClient.invalidateQueries({ queryKey: ["workflows", id, "runs"] });
      toast({ title: "Workflow started" });
    },
    onError: () => {
      toast({ title: "Failed to start workflow", variant: "destructive" });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/workflows/${id}/pause`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows", id] });
      toast({ title: "Workflow paused" });
    },
    onError: () => {
      toast({ title: "Failed to pause workflow", variant: "destructive" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      return api.delete(`/workflows/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      toast({ title: "Workflow deleted" });
      router.push("/workflows");
    },
    onError: () => {
      toast({ title: "Failed to delete workflow", variant: "destructive" });
    },
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
        <p className="text-lg font-medium">Workflow not found</p>
        <Button variant="outline" onClick={() => router.push("/workflows")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Workflows
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/workflows")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-muted p-2">
              <GitBranch className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{workflow.name}</h1>
              <p className="text-sm text-muted-foreground">{workflow.description || "No description"}</p>
            </div>
          </div>
          <Badge variant={statusVariant[workflow.status] || "secondary"}>
            {workflow.status}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["workflows", id] })}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {workflow.status === "active" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
            >
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || workflow.status === "completed"}
            >
              <Play className="h-4 w-4 mr-2" />
              Run
            </Button>
          )}
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-muted p-2">
                <History className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Runs</p>
                <p className="text-2xl font-bold">{workflow.run_count}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-muted p-2">
                <Clock className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Last Run</p>
                <p className="text-sm font-medium">
                  {workflow.last_run_at ? formatDate(workflow.last_run_at) : "Never"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-muted p-2">
                <Settings className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Trigger</p>
                <Badge variant="outline">{workflow.trigger}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Steps */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Pipeline Steps ({workflow.steps.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {workflow.steps.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No steps configured
            </p>
          ) : (
            <div className="space-y-2">
              {workflow.steps.map((step, i) => {
                const StepIcon = stepStatusIcon[step.status] || Clock;
                return (
                  <div key={step.id} className="flex items-center gap-3 p-3 rounded-lg border">
                    <span className="text-xs text-muted-foreground w-6">#{i + 1}</span>
                    <div className="flex items-center gap-2 flex-1">
                      <StepIcon className={`h-4 w-4 ${
                        step.status === "completed" ? "text-emerald-500" :
                        step.status === "failed" ? "text-red-500" :
                        step.status === "running" ? "text-amber-500 animate-spin" :
                        "text-muted-foreground"
                      }`} />
                      <div>
                        <p className="text-sm font-medium">{step.name}</p>
                        <p className="text-xs text-muted-foreground">{step.type}</p>
                      </div>
                    </div>
                    <Badge variant={
                      step.status === "completed" ? "success" :
                      step.status === "failed" ? "destructive" :
                      step.status === "running" ? "warning" :
                      "secondary"
                    }>
                      {step.status}
                    </Badge>
                    {i < workflow.steps.length - 1 && (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Run History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <History className="h-4 w-4" />
            Run History ({runs.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No runs yet
            </p>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
                <div key={run.id} className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <Badge variant={statusVariant[run.status] || "secondary"}>
                      {run.status}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium">
                        Step {run.current_step}/{run.total_steps}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Started {formatDate(run.started_at)}
                        {run.completed_at && ` — Completed ${formatDate(run.completed_at)}`}
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

      {/* Delete Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Workflow</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this workflow? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteMutation.mutate()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
