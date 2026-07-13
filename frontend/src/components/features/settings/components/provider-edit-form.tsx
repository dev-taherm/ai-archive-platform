"use client";

import {
  Save,
  TestTube,
  CheckCircle,
  Loader2,
  Trash2,
  Star,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ProviderConfig } from "@/types/api";

type ProviderType = "openai" | "google" | "ollama";

const PROVIDER_INFO: Record<
  ProviderType,
  { label: string; defaultBaseUrl: string; models: string[]; capabilities: string[] }
> = {
  ollama: {
    label: "Ollama (Local)",
    defaultBaseUrl: "http://localhost:11434",
    models: ["llama3.1", "mistral", "codellama", "phi3"],
    capabilities: ["llm"],
  },
  openai: {
    label: "OpenAI",
    defaultBaseUrl: "https://api.openai.com/v1",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    capabilities: ["llm", "embedding"],
  },
  google: {
    label: "Google Gemini",
    defaultBaseUrl: "https://generativelanguage.googleapis.com/v1beta",
    models: ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    capabilities: ["llm", "embedding"],
  },
};

export { PROVIDER_INFO };
export type { ProviderType };

interface ProviderEditFormProps {
  providers: ProviderConfig[];
  selectedId: string | null;
  isCreating: boolean;
  editName: string;
  editProviderType: ProviderType;
  editApiKey: string;
  editApiKeySet: boolean;
  editBaseUrl: string;
  editModel: string;
  editCapabilities: string[];
  onNameChange: (v: string) => void;
  onProviderTypeChange: (v: ProviderType) => void;
  onApiKeyChange: (v: string) => void;
  onBaseUrlChange: (v: string) => void;
  onModelChange: (v: string) => void;
  onCapabilitiesChange: (v: string[]) => void;
  onSave: () => void;
  onDelete: () => void;
  onSetDefault: () => void;
  onToggleActive: (provider: ProviderConfig) => void;
  onTest: () => void;
  onCancelNew: () => void;
  saving: boolean;
  testing: boolean;
  error: string;
  success: string;
  t: Function;
}

export default function ProviderEditForm({
  providers,
  selectedId,
  isCreating,
  editName,
  editProviderType,
  editApiKey,
  editApiKeySet,
  editBaseUrl,
  editModel,
  editCapabilities,
  onNameChange,
  onProviderTypeChange,
  onApiKeyChange,
  onBaseUrlChange,
  onModelChange,
  onCapabilitiesChange,
  onSave,
  onDelete,
  onSetDefault,
  onToggleActive,
  onTest,
  onCancelNew,
  saving,
  testing,
  error,
  success,
  t,
}: ProviderEditFormProps) {
  const activeProvider = providers.find((p) => p.is_default);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {isCreating ? t("newProvider") : t("editProvider")}
          </CardTitle>
          {!isCreating && selectedId && (
            <div className="flex gap-1.5">
              <Button
                size="sm"
                variant={activeProvider?.id === selectedId ? "brand" : "outline"}
                onClick={onSetDefault}
                disabled={activeProvider?.id === selectedId}
              >
                {activeProvider?.id === selectedId ? (
                  <>
                    <CheckCircle className="h-3.5 w-3.5 me-1" /> {t("default")}
                  </>
                ) : (
                  <>
                    <Star className="h-3.5 w-3.5 me-1" /> {t("setDefault")}
                  </>
                )}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  const p = providers.find((x) => x.id === selectedId);
                  if (p) onToggleActive(p);
                }}
              >
                {providers.find((x) => x.id === selectedId)?.is_active
                  ? t("disable")
                  : t("enable")}
              </Button>
              <Button size="sm" variant="destructive" onClick={onDelete}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isCreating || selectedId ? (
          <>
            {/* Provider Name */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("providerName")}</label>
              <Input
                value={editName}
                onChange={(e) => onNameChange(e.target.value)}
                placeholder={t("providerNamePlaceholder")}
              />
            </div>

            {/* Provider Type (2x2 button grid) */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("aiProvider")}</label>
              <div className="grid grid-cols-2 gap-2">
                {(Object.keys(PROVIDER_INFO) as ProviderType[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => onProviderTypeChange(p)}
                    className={`px-3 py-2 rounded-md border text-sm text-left transition-colors ${
                      editProviderType === p
                        ? "border-brand-teal bg-brand-teal/10 text-brand-teal"
                        : "border-brand-teal/10 hover:bg-muted"
                    }`}
                  >
                    {t(p === "google" ? "googleGemini" : p)}
                  </button>
                ))}
              </div>
            </div>

            {/* API Key */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("apiKey")}
                {editApiKeySet && !editApiKey && (
                  <span className="text-green-500 ml-2 text-xs">
                    {t("alreadySet")}
                  </span>
                )}
              </label>
              <Input
                type="password"
                value={editApiKey}
                onChange={(e) => onApiKeyChange(e.target.value)}
                placeholder={
                  editApiKeySet
                    ? t("enterNewKey")
                    : editProviderType === "ollama"
                      ? t("optionalForLocal")
                      : t("enterProviderKey", { provider: PROVIDER_INFO[editProviderType].label })
                }
              />
            </div>

            {/* Base URL */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("baseUrl")}</label>
              <Input
                value={editBaseUrl}
                onChange={(e) => onBaseUrlChange(e.target.value)}
                placeholder={PROVIDER_INFO[editProviderType].defaultBaseUrl}
              />
              <p className="text-xs text-muted-foreground">
                {t("defaultUrl", { url: PROVIDER_INFO[editProviderType].defaultBaseUrl })}
                {editProviderType === "ollama" &&
                  t("ollamaHint")}
                {editProviderType === "openai" &&
                  t("openaiHint")}
              </p>
            </div>

            {/* Model (with datalist autocomplete) */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("model")}</label>
              <Input
                value={editModel}
                onChange={(e) => onModelChange(e.target.value)}
                placeholder={PROVIDER_INFO[editProviderType].models[0]}
                list={`models-${editProviderType}`}
              />
              <datalist id={`models-${editProviderType}`}>
                {PROVIDER_INFO[editProviderType].models.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>

            {/* Capabilities */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("capabilities")}</label>
              <div className="flex gap-2">
                {["llm", "embedding"].map((cap) => (
                  <Badge
                    key={cap}
                    variant={
                      editCapabilities.includes(cap) ? "default" : "outline"
                    }
                    className="cursor-pointer"
                    onClick={() => {
                      onCapabilitiesChange(
                        editCapabilities.includes(cap)
                          ? editCapabilities.filter((c) => c !== cap)
                          : [...editCapabilities, cap]
                      );
                    }}
                  >
                    {cap}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <Button onClick={onSave} disabled={saving || !editName}>
                <Save className="me-2 h-4 w-4" />
                {saving
                  ? t("saving")
                  : isCreating
                    ? t("createProvider")
                    : t("saveAction")}
              </Button>
              {isCreating && (
                <Button variant="outline" onClick={onCancelNew}>
                  {t("cancelAction")}
                </Button>
              )}
              <Button
                variant="outline"
                onClick={onTest}
                disabled={testing || isCreating || !selectedId}
              >
                {testing ? (
                  <Loader2 className="me-2 h-4 w-4 animate-spin text-brand-teal" />
                ) : (
                  <TestTube className="me-2 h-4 w-4" />
                )}
                {testing ? t("testingConnection") : t("testConnection")}
              </Button>
            </div>
          </>
        ) : (
          <div className="text-sm text-muted-foreground text-center py-8">
            {t("selectProvider")}
          </div>
        )}

        {/* Feedback */}
        {error && <p className="text-sm text-red-500">{error}</p>}
        {success && <p className="text-sm text-green-500">{success}</p>}
      </CardContent>
    </Card>
  );
}
