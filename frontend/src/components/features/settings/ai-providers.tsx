"use client";

import { useState, useEffect } from "react";
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
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api";
import type { ProviderConfig } from "@/types/api";

const PROVIDER_TYPES = [
  { value: "openai", label: "OpenAI", capabilities: ["llm", "embedding"] },
  { value: "google", label: "Google Gemini", capabilities: ["llm", "embedding"] },
  { value: "ollama", label: "Ollama (Local)", capabilities: ["llm"] },
];

const DEFAULT_MODELS: Record<string, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "text-embedding-3-small", "text-embedding-3-large"],
  google: ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
  ollama: ["llama3.1", "mistral", "codellama", "phi3"],
};

export default function AIProviders() {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const { toast } = useToast();

  // Form state
  const [form, setForm] = useState({
    name: "",
    display_name: "",
    provider_type: "openai" as string,
    api_key: "",
    base_url: "",
    model_name: "",
    capabilities: ["llm"] as string[],
  });

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await api.get("/providers");
      setProviders(res.data);
    } catch {
      toast({ title: "Failed to load providers", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setForm({
      name: "",
      display_name: "",
      provider_type: "openai",
      api_key: "",
      base_url: "",
      model_name: "",
      capabilities: ["llm"],
    });
    setEditingId(null);
    setShowAdd(false);
  };

  const handleEdit = (provider: ProviderConfig) => {
    setForm({
      name: provider.name,
      display_name: provider.display_name,
      provider_type: provider.provider_type,
      api_key: "",
      base_url: provider.base_url,
      model_name: provider.model_name,
      capabilities: provider.capabilities,
    });
    setEditingId(provider.id);
    setShowAdd(true);
  };

  const handleSubmit = async () => {
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        display_name: form.display_name || form.name,
        provider_type: form.provider_type,
        capabilities: form.capabilities,
        base_url: form.base_url,
        model_name: form.model_name,
      };

      if (form.api_key) {
        payload.api_key = form.api_key;
      }

      if (editingId) {
        await api.put(`/providers/${editingId}`, payload);
        toast({ title: "Provider updated" });
      } else {
        await api.post("/providers", payload);
        toast({ title: "Provider added" });
      }

      resetForm();
      fetchProviders();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast({
        title: error.response?.data?.detail || "Failed to save provider",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this provider?")) return;
    try {
      await api.delete(`/providers/${id}`);
      toast({ title: "Provider deleted" });
      fetchProviders();
    } catch {
      toast({ title: "Failed to delete provider", variant: "destructive" });
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      await api.post(`/providers/${id}/set-default`);
      toast({ title: "Default provider updated" });
      fetchProviders();
    } catch {
      toast({ title: "Failed to set default", variant: "destructive" });
    }
  };

  const handleToggleActive = async (provider: ProviderConfig) => {
    try {
      await api.put(`/providers/${provider.id}`, {
        is_active: !provider.is_active,
      });
      fetchProviders();
    } catch {
      toast({ title: "Failed to update provider", variant: "destructive" });
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Loading providers...
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">AI Providers</h3>
          <p className="text-sm text-muted-foreground">
            Configure LLM and embedding providers for AI features
          </p>
        </div>
        <Button size="sm" onClick={() => { resetForm(); setShowAdd(true); }}>
          Add Provider
        </Button>
      </div>

      {/* Provider List */}
      {providers.length === 0 && !showAdd && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No providers configured. Add one to enable AI features.
          </CardContent>
        </Card>
      )}

      {providers.map((provider) => (
        <Card key={provider.id}>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{provider.display_name}</span>
                    {provider.is_default && (
                      <Badge variant="success">Default</Badge>
                    )}
                    {!provider.is_active && (
                      <Badge variant="secondary">Disabled</Badge>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {provider.provider_type} &middot; {provider.model_name || "No model set"} &middot;{" "}
                    {provider.api_key_set ? "API key set" : "No API key"}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSetDefault(provider.id)}
                  disabled={provider.is_default}
                >
                  Set Default
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleToggleActive(provider)}
                >
                  {provider.is_active ? "Disable" : "Enable"}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => handleEdit(provider)}>
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() => handleDelete(provider.id)}
                >
                  Delete
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}

      {/* Add/Edit Form */}
      {showAdd && (
        <Card>
          <CardHeader>
            <CardTitle>{editingId ? "Edit Provider" : "Add Provider"}</CardTitle>
            <CardDescription>
              Configure an AI provider for LLM and/or embedding capabilities
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Provider Type</label>
                <select
                  value={form.provider_type}
                  onChange={(e) => {
                    const pt = e.target.value;
                    const caps = PROVIDER_TYPES.find((p) => p.value === pt)?.capabilities || ["llm"];
                    setForm({ ...form, provider_type: pt, capabilities: caps, model_name: "" });
                  }}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {PROVIDER_TYPES.map((pt) => (
                    <option key={pt.value} value={pt.value}>
                      {pt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Model</label>
                <select
                  value={form.model_name}
                  onChange={(e) => setForm({ ...form, model_name: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">Select model...</option>
                  {(DEFAULT_MODELS[form.provider_type] || []).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Name</label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="my-openai"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Display Name</label>
                <Input
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="My OpenAI Config"
                />
              </div>
            </div>

            {form.provider_type !== "ollama" && (
              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <Input
                  type="password"
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  placeholder={editingId ? "Leave blank to keep existing" : "sk-..."}
                />
              </div>
            )}

            {form.provider_type === "ollama" && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Base URL</label>
                <Input
                  value={form.base_url}
                  onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                  placeholder="http://localhost:11434"
                />
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Capabilities</label>
              <div className="flex gap-2">
                {["llm", "embedding"].map((cap) => (
                  <Badge
                    key={cap}
                    variant={form.capabilities.includes(cap) ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => {
                      const caps = form.capabilities.includes(cap)
                        ? form.capabilities.filter((c) => c !== cap)
                        : [...form.capabilities, cap];
                      setForm({ ...form, capabilities: caps });
                    }}
                  >
                    {cap}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button onClick={handleSubmit}>
                {editingId ? "Update" : "Add"} Provider
              </Button>
              <Button variant="outline" onClick={resetForm}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
