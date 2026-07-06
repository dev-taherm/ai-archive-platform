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
  X,
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

const STEP_TYPES = [
  { value: "scan", label: "Scan Folder" },
  { value: "ocr", label: "OCR" },
  { value: "classify", label: "Classify" },
  { value: "summarize", label: "Summarize" },
  { value: "extract_metadata", label: "Extract Metadata" },
  { value: "embed", label: "Generate Embeddings" },
  { value: "index", label: "Index to Vector Store" },
  { value: "notify", label: "Notify" },
  { value: "store", label: "Store Result" },
];

const TRIGGER_TYPES = [
  { value: "manual", label: "Manual" },
  { value: "on_upload", label: "On Upload" },
  { value: "scheduled", label: "Scheduled" },
];

interface CreateFormState {
  name: string;
  description: string;
  trigger_type: string;
  steps: { type: string; name: string; config: Record<string, unknown> }[];
}

const emptyCreateForm: CreateFormState = {
  name: "",
  description: "",
  trigger_type: "manual",
  steps: [],
};

export default function WorkflowsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [expandedWorkflow, setExpandedWorkflow] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateFormState>(emptyCreateForm);

  const { data: workflows = [], isLoading } = useQuery<Workflow[]>({
    queryKey: ["workflows"],
    queryFn: async () => {
      const res = await api.get("/workflows");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data: CreateFormState) => {
      const payload: Record<string, unknown> = {
        name: data.name,
        description: data.description,
        trigger_type: data.trigger_type,
        steps: data.steps.map((s, i) => ({
          ...s,
          name: s.name || `Step ${i + 1}`,
        })),
      };
      const res = await api.post("/workflows", payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      setShowCreate(false);
      setForm(emptyCreateForm);
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

  const addStep = () => {
    setForm((prev) => ({
      ...prev,
      steps: [...prev.steps, { type: "classify", name: "", config: {} }],
    }));
  };

  const removeStep = (index: number) => {
    setForm((prev) => ({
      ...prev,
      steps: prev.steps.filter((_, i) => i !== index),
    }));
  };

  const updateStep = (index: number, field: string, value: string) => {
    setForm((prev) => ({
      ...prev,
      steps: prev.steps.map((s, i) =>
        i === index ? { ...s, [field]: value } : s
      ),
    }));
  };

  const handleCreate = () => {
    if (!form.name.trim()) return;
    createMutation.mutate(form);
  };

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
          <Button onClick={() => setShowCreate(!showCreate)}>
            <Plus className="mr-2 h-4 w-4" />
            New Workflow
          </Button>
        </div>
      </div>

      {showCreate && (
        <Card className="border-dashed">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Create Workflow</CardTitle>
                <CardDescription>Define a new automation pipeline</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowCreate(false);
                  setForm(emptyCreateForm);
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Name *</label>
                <Input
                  placeholder="e.g., Document Processing Pipeline"
                  value={form.name}
                  onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Description</label>
                <Input
                  placeholder="What this workflow does"
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Trigger</label>
              <div className="flex gap-2">
                {TRIGGER_TYPES.map((t) => (
                  <Button
                    key={t.value}
                    variant={form.trigger_type === t.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setForm((p) => ({ ...p, trigger_type: t.value }))}
                  >
                    {t.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Steps</label>
                <Button variant="outline" size="sm" onClick={addStep}>
                  <Plus className="mr-1 h-3 w-3" />
                  Add Step
                </Button>
              </div>
              {form.steps.length === 0 ? (
                <p className="text-sm text-muted-foreground py-2">No steps added yet. Click "Add Step" to begin.</p>
              ) : (
                <div className="space-y-2">
                  {form.steps.map((step, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground w-6">#{i + 1}</span>
                      <select
                        value={step.type}
                        onChange={(e) => updateStep(i, "type", e.target.value)}
                        className="flex h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      >
                        {STEP_TYPES.map((st) => (
                          <option key={st.value} value={st.value}>
                            {st.label}
                          </option>
                        ))}
                      </select>
                      <Input
                        placeholder={`Step ${i + 1} name`}
                        value={step.name}
                        onChange={(e) => updateStep(i, "name", e.target.value)}
                        className="flex-1"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeStep(i)}
                        className="text-destructive"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowCreate(false);
                  setForm(emptyCreateForm);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!form.name.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                Create Workflow
              </Button>
            </div>

            {createMutation.isError && (
              <p className="text-sm text-destructive">
                Failed to create workflow. Please try again.
              </p>
            )}
          </CardContent>
        </Card>
      )}

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
