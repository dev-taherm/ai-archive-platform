"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  GitBranch,
  Play,
  Pause,
  Trash2,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Plus,
  ChevronRight,
} from "lucide-react";
import api from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

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

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning"> = {
  draft: "secondary",
  active: "success",
  paused: "warning",
  completed: "success",
  failed: "destructive",
};

const stepStatusIcon: Record<string, typeof Clock> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle,
  failed: XCircle,
  skipped: Clock,
};

export default function WorkflowsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [expandedWorkflow, setExpandedWorkflow] = useState<string | null>(null);

  const { data: workflows = [], isLoading } = useQuery<Workflow[]>({
    queryKey: ["workflows"],
    queryFn: async () => {
      const res = await api.get<Workflow[]>("/workflows");
      return res.data;
    },
  });

  const runMutation = useMutation({
    mutationFn: async (workflowId: string) => {
      await api.post(`/workflows/${workflowId}/run`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: async (workflowId: string) => {
      await api.post(`/workflows/${workflowId}/pause`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (workflowId: string) => {
      await api.delete(`/workflows/${workflowId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
  });

  const filtered = workflows.filter(
    (w) =>
      w.name.toLowerCase().includes(search.toLowerCase()) ||
      w.description?.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: workflows.length,
    active: workflows.filter((w) => w.status === "active").length,
    completed: workflows.filter((w) => w.status === "completed").length,
    failed: workflows.filter((w) => w.status === "failed").length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workflows</h1>
          <p className="text-muted-foreground">
            Automate document processing pipelines
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["workflows"] })}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Workflow
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Workflows</CardDescription>
            <CardTitle className="text-2xl">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-2xl text-emerald-600">{stats.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Completed</CardDescription>
            <CardTitle className="text-2xl text-blue-600">{stats.completed}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Failed</CardDescription>
            <CardTitle className="text-2xl text-red-600">{stats.failed}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Search workflows..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8 text-muted-foreground">
              Loading workflows...
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <GitBranch className="mb-4 h-12 w-12 opacity-50" />
              <p className="text-lg font-medium">No workflows found</p>
              <p className="text-sm">
                {search ? "Try a different search term" : "Create a workflow to automate your document processing"}
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
                    onClick={() =>
                      setExpandedWorkflow(
                        expandedWorkflow === workflow.id ? null : workflow.id
                      )
                    }
                  >
                    <div className="flex items-center gap-3">
                      <GitBranch className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">{workflow.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {workflow.description || "No description"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={statusVariant[workflow.status] || "secondary"}>
                        {workflow.status}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {workflow.run_count} runs
                      </span>
                      <ChevronRight
                        className={`h-4 w-4 transition-transform ${
                          expandedWorkflow === workflow.id ? "rotate-90" : ""
                        }`}
                      />
                    </div>
                  </div>

                  {expandedWorkflow === workflow.id && (
                    <div className="border-t p-4 space-y-4">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Trigger: </span>
                          <Badge variant="outline">{workflow.trigger}</Badge>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Last run: </span>
                          {workflow.last_run_at ? formatDateTime(workflow.last_run_at) : "Never"}
                        </div>
                      </div>

                      {workflow.steps.length > 0 && (
                        <div>
                          <p className="text-sm font-medium mb-2">Steps</p>
                          <div className="flex items-center gap-2 flex-wrap">
                            {workflow.steps.map((step, i) => {
                              const StepIcon = stepStatusIcon[step.status] || Clock;
                              return (
                                <div key={step.id} className="flex items-center gap-1">
                                  {i > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
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
                            onClick={() => pauseMutation.mutate(workflow.id)}
                            disabled={pauseMutation.isPending}
                          >
                            <Pause className="mr-1 h-3.5 w-3.5" />
                            Pause
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => runMutation.mutate(workflow.id)}
                            disabled={runMutation.isPending || workflow.status === "completed"}
                          >
                            <Play className="mr-1 h-3.5 w-3.5" />
                            Run
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          onClick={() => deleteMutation.mutate(workflow.id)}
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="mr-1 h-3.5 w-3.5" />
                          Delete
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
    </div>
  );
}
