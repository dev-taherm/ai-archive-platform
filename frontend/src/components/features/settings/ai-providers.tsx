"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
  Bot,
  Save,
  TestTube,
  CheckCircle,
  XCircle,
  Loader2,
  Plus,
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
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api";
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

export default function AIProviders() {
  const t = useTranslations("settings");
  const { toast } = useToast();

  // ── Provider list state ──
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  // ── Edit form state (per-field, matching reference pattern) ──
  const [editName, setEditName] = useState("");
  const [editProviderType, setEditProviderType] = useState<ProviderType>("openai");
  const [editApiKey, setEditApiKey] = useState("");
  const [editApiKeySet, setEditApiKeySet] = useState(false);
  const [editBaseUrl, setEditBaseUrl] = useState("");
  const [editModel, setEditModel] = useState("");
  const [editCapabilities, setEditCapabilities] = useState<string[]>(["llm"]);

  // ── UI feedback ──
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  // ── Load providers ──
  useEffect(() => {
    fetchProviders();
  }, []);

  // Auto-select first provider after load
  useEffect(() => {
    if (!loading && !selectedId && !isCreating && providers.length > 0) {
      const id = requestAnimationFrame(() => setSelectedId(providers[0].id));
      return () => cancelAnimationFrame(id);
    }
  }, [loading, selectedId, isCreating, providers]);

  // ── Load selected provider into form ──
  useEffect(() => {
    if (isCreating) return;
    const p = providers.find((x) => x.id === selectedId);
    const id = requestAnimationFrame(() => {
      if (!p) {
        setEditName("");
        setEditProviderType("openai");
        setEditApiKey("");
        setEditApiKeySet(false);
        setEditBaseUrl(PROVIDER_INFO.openai.defaultBaseUrl);
        setEditModel(PROVIDER_INFO.openai.models[0]);
        setEditCapabilities(["llm"]);
        return;
      }
      setEditName(p.name);
      setEditProviderType(p.provider_type as ProviderType);
      setEditApiKey("");
      setEditApiKeySet(p.api_key_set);
      setEditBaseUrl(p.base_url || PROVIDER_INFO[p.provider_type as ProviderType]?.defaultBaseUrl || "");
      setEditModel(p.model_name);
      setEditCapabilities(p.capabilities);
    });
    return () => cancelAnimationFrame(id);
  }, [selectedId, providers, isCreating]);

  const fetchProviders = async () => {
    try {
      const res = await api.get("/providers");
      setProviders(res.data);
    } catch {
      toast({ title: t("failedToLoadProviders"), variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  // ── New provider ──
  const handleNew = () => {
    setIsCreating(true);
    setSelectedId(null);
    setEditName("");
    setEditProviderType("openai");
    setEditApiKey("");
    setEditApiKeySet(false);
    setEditBaseUrl(PROVIDER_INFO.openai.defaultBaseUrl);
    setEditModel(PROVIDER_INFO.openai.models[0]);
    setEditCapabilities(["llm"]);
    setError("");
    setSuccess("");
    setTestResult(null);
  };

  // ── Cancel new ──
  const handleCancelNew = () => {
    setIsCreating(false);
    if (providers.length > 0) setSelectedId(providers[0].id);
  };

  // ── Provider change (resets form fields) ──
  const handleProviderChange = (newProvider: ProviderType) => {
    setEditProviderType(newProvider);
    setEditBaseUrl(PROVIDER_INFO[newProvider].defaultBaseUrl);
    setEditModel(PROVIDER_INFO[newProvider].models[0]);
    setEditApiKey("");
    setEditApiKeySet(false);
    setEditCapabilities(PROVIDER_INFO[newProvider].capabilities);
    setTestResult(null);
  };

  // ── Save provider (create or update) ──
  const handleSave = async () => {
    setError("");
    setSuccess("");
    setSaving(true);

    try {
      const payload: Record<string, unknown> = {
        name: editName,
        display_name: editName,
        provider_type: editProviderType,
        capabilities: editCapabilities,
        base_url: editBaseUrl,
        model_name: editModel,
      };

      if (editApiKey) {
        payload.api_key = editApiKey;
      }

      if (isCreating) {
        const res = await api.post("/providers", payload);
        toast({ title: t("providerAdded") });
        setProviders((prev) => [...prev, res.data]);
        setSelectedId(res.data.id);
        setIsCreating(false);
        setSuccess(t("providerCreated"));
        if (editApiKey) setEditApiKeySet(true);
      } else if (selectedId) {
        await api.put(`/providers/${selectedId}`, payload);
        toast({ title: t("providerUpdated") });
        setSuccess(t("providerSaved"));
        if (editApiKey) setEditApiKeySet(true);
        fetchProviders();
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || t("failedToSave"));
    } finally {
      setSaving(false);
    }
  };

  // ── Delete provider ──
  const handleDelete = async () => {
    if (!selectedId) return;
    if (!confirm(t("deleteConfirm"))) return;

    try {
      await api.delete(`/providers/${selectedId}`);
      toast({ title: t("providerDeleted") });
      setProviders((prev) => prev.filter((p) => p.id !== selectedId));
      setSelectedId(null);
      setSuccess(t("providerDeleted"));
    } catch {
      toast({ title: t("failedToDeleteProvider"), variant: "destructive" });
    }
  };

  // ── Set default ──
  const handleSetDefault = async () => {
    if (!selectedId) return;

    try {
      await api.post(`/providers/${selectedId}/set-default`);
      toast({ title: t("defaultUpdated") });
      setProviders((prev) =>
        prev.map((p) => ({ ...p, is_default: p.id === selectedId }))
      );
      setSuccess(t("defaultUpdated"));
    } catch {
      toast({ title: t("failedToSetDefault"), variant: "destructive" });
    }
  };

  // ── Toggle active ──
  const handleToggleActive = async (provider: ProviderConfig) => {
    try {
      await api.put(`/providers/${provider.id}`, {
        is_active: !provider.is_active,
      });
      fetchProviders();
    } catch {
      toast({ title: t("failedToUpdateProvider"), variant: "destructive" });
    }
  };

  // ── Test connection ──
  const handleTest = async () => {
    if (!selectedId) return;

    setTesting(true);
    setTestResult(null);

    try {
      // Save first so we test the current config
      const payload: Record<string, unknown> = {
        name: editName,
        display_name: editName,
        provider_type: editProviderType,
        capabilities: editCapabilities,
        base_url: editBaseUrl,
        model_name: editModel,
      };
      if (editApiKey) {
        payload.api_key = editApiKey;
      }
      await api.put(`/providers/${selectedId}`, payload);
      if (editApiKey) setEditApiKeySet(true);
      fetchProviders();

      // Now test the provider
      const res = await api.post(`/providers/${selectedId}/test`);
      const data = res.data;

      setTestResult({
        ok: data.success,
        message: data.success
          ? t("testResult", { detail: data.detail, preview: data.response_preview })
          : data.detail,
      });
    } catch (err: unknown) {
      const error = err as {
        response?: { data?: { detail?: string; success?: boolean } };
      };
      const detail =
        error.response?.data?.detail || t("connectionFailed");
      setTestResult({ ok: false, message: detail });
    } finally {
      setTesting(false);
    }
  };

  const activeProvider = providers.find((p) => p.is_default);

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          {t("loadingProviders")}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent flex items-center gap-2">
        <Bot className="h-6 w-6" />
        {t("providers")}
      </h1>

      {/* ── Master-Detail Layout ── */}
      <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-4">
        {/* Provider List */}
        <Card className="md:row-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{t("providers")}</CardTitle>
              <Button size="sm" variant="outline" onClick={handleNew}>
                <Plus className="h-3.5 w-3.5 me-1" />
                {t("new")}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-2">
            {providers.length === 0 && !isCreating ? (
              <div className="p-4 text-sm text-muted-foreground text-center">
                {t("noProviders")}
              </div>
            ) : (
              <div className="space-y-1">
                {providers.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setSelectedId(p.id);
                      setIsCreating(false);
                      setError("");
                      setSuccess("");
                      setTestResult(null);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center gap-2 ${
                      selectedId === p.id && !isCreating
                        ? "bg-brand-teal/10 text-brand-teal border border-brand-teal/20"
                        : "hover:bg-muted border border-transparent"
                    }`}
                  >
                    {p.is_default && (
                      <Star className="h-3.5 w-3.5 text-yellow-500 shrink-0 fill-yellow-500" />
                    )}
                    <span className="truncate flex-1">{p.name}</span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {t(p.provider_type === "google" ? "googleGemini" : p.provider_type)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit Form */}
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
                    onClick={handleSetDefault}
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
                      if (p) handleToggleActive(p);
                    }}
                  >
                    {providers.find((x) => x.id === selectedId)?.is_active
                      ? t("disable")
                      : t("enable")}
                  </Button>
                  <Button size="sm" variant="destructive" onClick={handleDelete}>
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
                    onChange={(e) => setEditName(e.target.value)}
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
                        onClick={() => handleProviderChange(p)}
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
                    onChange={(e) => setEditApiKey(e.target.value)}
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
                    onChange={(e) => setEditBaseUrl(e.target.value)}
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
                    onChange={(e) => setEditModel(e.target.value)}
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
                          setEditCapabilities((prev) =>
                            prev.includes(cap)
                              ? prev.filter((c) => c !== cap)
                              : [...prev, cap]
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
                  <Button onClick={handleSave} disabled={saving || !editName}>
                    <Save className="me-2 h-4 w-4" />
                    {saving
                      ? t("saving")
                      : isCreating
                        ? t("createProvider")
                        : t("saveAction")}
                  </Button>
                  {isCreating && (
                    <Button variant="outline" onClick={handleCancelNew}>
                      {t("cancelAction")}
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={handleTest}
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

            {testResult && (
              <div
                className={`flex items-start gap-2 p-3 rounded-md text-sm ${
                  testResult.ok
                    ? "bg-green-500/10 text-green-600 dark:text-green-400"
                    : "bg-red-500/10 text-red-600 dark:text-red-400"
                }`}
              >
                {testResult.ok ? (
                  <CheckCircle className="h-4 w-4 mt-0.5 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
                )}
                <span>{testResult.message}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
