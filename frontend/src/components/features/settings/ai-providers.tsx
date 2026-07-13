"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Bot } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api";
import type { ProviderConfig } from "@/types/api";
import ProviderListSidebar from "./components/provider-list-sidebar";
import ProviderEditForm, { type ProviderType, PROVIDER_INFO } from "./components/provider-edit-form";
import TestResultBanner from "./components/test-result-banner";

export default function AIProviders() {
  const t = useTranslations("settings");
  const { toast } = useToast();

  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  const [editName, setEditName] = useState("");
  const [editProviderType, setEditProviderType] = useState<ProviderType>("openai");
  const [editApiKey, setEditApiKey] = useState("");
  const [editApiKeySet, setEditApiKeySet] = useState(false);
  const [editBaseUrl, setEditBaseUrl] = useState("");
  const [editModel, setEditModel] = useState("");
  const [editCapabilities, setEditCapabilities] = useState<string[]>(["llm"]);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => { fetchProviders(); }, []);

  useEffect(() => {
    if (!loading && !selectedId && !isCreating && providers.length > 0) {
      const id = requestAnimationFrame(() => setSelectedId(providers[0].id));
      return () => cancelAnimationFrame(id);
    }
  }, [loading, selectedId, isCreating, providers]);

  useEffect(() => {
    if (isCreating) return;
    const p = providers.find((x) => x.id === selectedId);
    const id = requestAnimationFrame(() => {
      if (!p) {
        setEditName(""); setEditProviderType("openai"); setEditApiKey(""); setEditApiKeySet(false);
        setEditBaseUrl(PROVIDER_INFO.openai.defaultBaseUrl); setEditModel(PROVIDER_INFO.openai.models[0]);
        setEditCapabilities(["llm"]); return;
      }
      setEditName(p.name); setEditProviderType(p.provider_type as ProviderType);
      setEditApiKey(""); setEditApiKeySet(p.api_key_set);
      setEditBaseUrl(p.base_url || PROVIDER_INFO[p.provider_type as ProviderType]?.defaultBaseUrl || "");
      setEditModel(p.model_name); setEditCapabilities(p.capabilities);
    });
    return () => cancelAnimationFrame(id);
  }, [selectedId, providers, isCreating]);

  const fetchProviders = async () => {
    try {
      const res = await api.get("/providers");
      setProviders(res.data);
    } catch (error) {
      console.error("Failed to fetch providers:", error);
      toast({ title: t("failedToLoadProviders"), variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleNew = () => {
    setIsCreating(true); setSelectedId(null); setEditName("");
    setEditProviderType("openai"); setEditApiKey(""); setEditApiKeySet(false);
    setEditBaseUrl(PROVIDER_INFO.openai.defaultBaseUrl);
    setEditModel(PROVIDER_INFO.openai.models[0]);
    setEditCapabilities(["llm"]); setError(""); setSuccess(""); setTestResult(null);
  };

  const handleCancelNew = () => {
    setIsCreating(false);
    if (providers.length > 0) setSelectedId(providers[0].id);
  };

  const handleProviderChange = (newProvider: ProviderType) => {
    setEditProviderType(newProvider);
    setEditBaseUrl(PROVIDER_INFO[newProvider].defaultBaseUrl);
    setEditModel(PROVIDER_INFO[newProvider].models[0]);
    setEditApiKey(""); setEditApiKeySet(false);
    setEditCapabilities(PROVIDER_INFO[newProvider].capabilities);
    setTestResult(null);
  };

  const buildPayload = () => ({
    name: editName, display_name: editName, provider_type: editProviderType,
    capabilities: editCapabilities, base_url: editBaseUrl, model_name: editModel,
    ...(editApiKey ? { api_key: editApiKey } : {}),
  });

  const handleSave = async () => {
    setError(""); setSuccess(""); setSaving(true);
    try {
      if (isCreating) {
        const res = await api.post("/providers", buildPayload());
        toast({ title: t("providerAdded") });
        setProviders((prev) => [...prev, res.data]);
        setSelectedId(res.data.id); setIsCreating(false);
        setSuccess(t("providerCreated")); if (editApiKey) setEditApiKeySet(true);
      } else if (selectedId) {
        await api.put(`/providers/${selectedId}`, buildPayload());
        toast({ title: t("providerUpdated") });
        setSuccess(t("providerSaved")); if (editApiKey) setEditApiKeySet(true);
        fetchProviders();
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || t("failedToSave"));
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    if (!confirm(t("deleteConfirm"))) return;
    try {
      await api.delete(`/providers/${selectedId}`);
      toast({ title: t("providerDeleted") });
      setProviders((prev) => prev.filter((p) => p.id !== selectedId));
      setSelectedId(null); setSuccess(t("providerDeleted"));
    } catch (error) {
      console.error("Failed to delete provider:", error);
      toast({ title: t("failedToDeleteProvider"), variant: "destructive" });
    }
  };

  const handleSetDefault = async () => {
    if (!selectedId) return;
    try {
      await api.post(`/providers/${selectedId}/set-default`);
      toast({ title: t("defaultUpdated") });
      setProviders((prev) => prev.map((p) => ({ ...p, is_default: p.id === selectedId })));
      setSuccess(t("defaultUpdated"));
    } catch (error) {
      console.error("Failed to set default provider:", error);
      toast({ title: t("failedToSetDefault"), variant: "destructive" });
    }
  };

  const handleToggleActive = async (provider: ProviderConfig) => {
    try {
      await api.put(`/providers/${provider.id}`, { is_active: !provider.is_active });
      fetchProviders();
    } catch (error) {
      console.error("Failed to toggle provider active state:", error);
      toast({ title: t("failedToUpdateProvider"), variant: "destructive" });
    }
  };

  const handleTest = async () => {
    if (!selectedId) return;
    setTesting(true); setTestResult(null);
    try {
      await api.put(`/providers/${selectedId}`, buildPayload());
      if (editApiKey) setEditApiKeySet(true);
      fetchProviders();
      const res = await api.post(`/providers/${selectedId}/test`);
      const data = res.data;
      setTestResult({
        ok: data.success,
        message: data.success
          ? t("testResult", { detail: data.detail, preview: data.response_preview })
          : data.detail,
      });
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setTestResult({ ok: false, message: e.response?.data?.detail || t("connectionFailed") });
    } finally { setTesting(false); }
  };

  const handleSelect = (id: string) => {
    setSelectedId(id); setIsCreating(false); setError(""); setSuccess(""); setTestResult(null);
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">{t("loadingProviders")}</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent flex items-center gap-2">
        <Bot className="h-6 w-6" /> {t("providers")}
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-4">
        <ProviderListSidebar providers={providers} selectedId={selectedId} isCreating={isCreating} onSelect={handleSelect} onNew={handleNew} t={t} />
        <ProviderEditForm
          providers={providers} selectedId={selectedId} isCreating={isCreating}
          editName={editName} editProviderType={editProviderType} editApiKey={editApiKey}
          editApiKeySet={editApiKeySet} editBaseUrl={editBaseUrl} editModel={editModel} editCapabilities={editCapabilities}
          onNameChange={setEditName} onProviderTypeChange={handleProviderChange} onApiKeyChange={setEditApiKey}
          onBaseUrlChange={setEditBaseUrl} onModelChange={setEditModel} onCapabilitiesChange={setEditCapabilities}
          onSave={handleSave} onDelete={handleDelete} onSetDefault={handleSetDefault}
          onToggleActive={handleToggleActive} onTest={handleTest} onCancelNew={handleCancelNew}
          saving={saving} testing={testing} error={error} success={success} t={t}
        />
      </div>
      <TestResultBanner testResult={testResult} t={t} />
    </div>
  );
}
