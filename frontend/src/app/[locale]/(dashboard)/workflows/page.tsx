"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Plus } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import type { Workflow } from "@/types/api";
import WorkflowCreateForm from "./components/workflow-create-form";
import WorkflowStatsGrid from "./components/workflow-stats-grid";
import WorkflowList from "./components/workflow-list";

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
  const t = useTranslations("workflows");
  const tc = useTranslations("common");
  const queryClient = useQueryClient();

  const STEP_TYPES = [
    { value: "scan", label: t("scanFolder") },
    { value: "ocr", label: t("ocr") },
    { value: "classify", label: t("classify") },
    { value: "summarize", label: t("summarize") },
    { value: "extract_metadata", label: t("extractMetadata") },
    { value: "embed", label: t("generateEmbeddings") },
    { value: "index", label: t("indexToVectorStore") },
    { value: "notify", label: t("notify") },
    { value: "store", label: t("storeResult") },
  ];

  const TRIGGER_TYPES = [
    { value: "manual", label: t("manual") },
    { value: "on_upload", label: t("onUpload") },
    { value: "scheduled", label: t("scheduled") },
  ];

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
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">
            {t("title")}
          </h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() =>
              queryClient.invalidateQueries({ queryKey: ["workflows"] })
            }
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t("refresh")}
          </Button>
          <Button onClick={() => setShowCreate(!showCreate)}>
            <Plus className="mr-2 h-4 w-4" />
            {t("newWorkflow")}
          </Button>
        </div>
      </div>

      {showCreate && (
        <WorkflowCreateForm
          form={form}
          onFormChange={setForm}
          onSubmit={handleCreate}
          onCancel={() => {
            setShowCreate(false);
            setForm(emptyCreateForm);
          }}
          onAddStep={addStep}
          onRemoveStep={removeStep}
          onUpdateStep={updateStep}
          creating={createMutation.isPending}
          createError={createMutation.isError}
          t={t}
          tc={tc}
          stepTypes={STEP_TYPES}
          triggerTypes={TRIGGER_TYPES}
        />
      )}

      <WorkflowStatsGrid stats={stats} t={t} />

      <WorkflowList
        workflows={workflows}
        isLoading={isLoading}
        search={search}
        onSearchChange={setSearch}
        expandedId={expandedWorkflow}
        onToggleExpand={(id) =>
          setExpandedWorkflow(expandedWorkflow === id ? null : id)
        }
        onRun={(id) => runMutation.mutate(id)}
        onPause={(id) => pauseMutation.mutate(id)}
        onDelete={(id) => deleteMutation.mutate(id)}
        running={{
          [runMutation.variables || ""]: runMutation.isPending,
        }}
        t={t}
        tc={tc}
      />
    </div>
  );
}
