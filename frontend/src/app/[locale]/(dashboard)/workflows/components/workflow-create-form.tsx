"use client";

import { Loader2, Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export interface CreateFormState {
  name: string;
  description: string;
  trigger_type: string;
  steps: { type: string; name: string; config: Record<string, unknown> }[];
}

type Translator = ReturnType<typeof useTranslations>;

interface WorkflowCreateFormProps {
  form: CreateFormState;
  onFormChange: (form: CreateFormState) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onAddStep: () => void;
  onRemoveStep: (index: number) => void;
  onUpdateStep: (index: number, field: string, value: string) => void;
  creating: boolean;
  createError: boolean;
  t: Translator;
  tc: Translator;
  stepTypes: { value: string; label: string }[];
  triggerTypes: { value: string; label: string }[];
}

export default function WorkflowCreateForm({
  form,
  onFormChange,
  onSubmit,
  onCancel,
  onAddStep,
  onRemoveStep,
  onUpdateStep,
  creating,
  createError,
  t,
  tc,
  stepTypes,
  triggerTypes,
}: WorkflowCreateFormProps) {
  return (
    <Card className="border-dashed">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{t("createWorkflow")}</CardTitle>
            <CardDescription>{t("createDescription")}</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onCancel}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("name")}</label>
            <Input
              placeholder={t("namePlaceholder")}
              value={form.name}
              onChange={(e) => onFormChange({ ...form, name: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("description")}</label>
            <Input
              placeholder={t("descriptionPlaceholder")}
              value={form.description}
              onChange={(e) =>
                onFormChange({ ...form, description: e.target.value })
              }
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">{t("trigger")}</label>
          <div className="flex gap-2">
            {triggerTypes.map((trig) => (
              <Button
                key={trig.value}
                variant={form.trigger_type === trig.value ? "default" : "outline"}
                size="sm"
                onClick={() =>
                  onFormChange({ ...form, trigger_type: trig.value })
                }
              >
                {trig.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">{t("steps")}</label>
            <Button variant="outline" size="sm" onClick={onAddStep}>
              <Plus className="mr-1 h-3 w-3" />
              {t("addStep")}
            </Button>
          </div>
          {form.steps.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">{t("noSteps")}</p>
          ) : (
            <div className="space-y-2">
              {form.steps.map((step, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-6">
                    #{i + 1}
                  </span>
                  <select
                    value={step.type}
                    onChange={(e) => onUpdateStep(i, "type", e.target.value)}
                    className="flex h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    {stepTypes.map((st) => (
                      <option key={st.value} value={st.value}>
                        {st.label}
                      </option>
                    ))}
                  </select>
                  <Input
                    placeholder={`Step ${i + 1} name`}
                    value={step.name}
                    onChange={(e) => onUpdateStep(i, "name", e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRemoveStep(i)}
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
          <Button variant="outline" onClick={onCancel}>
            {tc("cancel")}
          </Button>
          <Button
            onClick={onSubmit}
            disabled={!form.name.trim() || creating}
          >
            {creating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-brand-teal" />
            ) : (
              <Plus className="mr-2 h-4 w-4" />
            )}
            {t("createWorkflow")}
          </Button>
        </div>

        {createError && (
          <p className="text-sm text-destructive">{t("createFailed")}</p>
        )}
      </CardContent>
    </Card>
  );
}
