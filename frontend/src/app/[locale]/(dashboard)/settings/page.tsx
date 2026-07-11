"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/hooks/use-auth";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api";
import AIProviders from "@/components/features/settings/ai-providers";
import OrganizationSettings from "@/components/features/settings/organization-settings";
import {
  User,
  Palette,
  Key,
  Brain,
  Trash2,
  Plus,
  Eye,
  EyeOff,
  Building2,
} from "lucide-react";

interface ApiKey {
  id: string;
  name: string;
  key_preview: string;
  created_at: string;
  last_used: string | null;
}

type Tab = "profile" | "appearance" | "api-keys" | "ai-providers" | "organization";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tc = useTranslations("common");
  const { user } = useAuth();
  const { theme, setTheme } = useUIStore();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<Tab>("profile");

  const tabs: { id: Tab; label: string; icon: typeof User }[] = [
    { id: "profile", label: t("profile"), icon: User },
    { id: "organization", label: t("organization"), icon: Building2 },
    { id: "appearance", label: t("appearance"), icon: Palette },
    { id: "api-keys", label: t("apiKeys"), icon: Key },
    { id: "ai-providers", label: t("aiProviders"), icon: Brain },
  ];
  const [firstName, setFirstName] = useState(user?.first_name || "");
  const [lastName, setLastName] = useState(user?.last_name || "");
  const [saving, setSaving] = useState(false);

  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [showNewKey, setShowNewKey] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/users/${user?.id}/`, {
        first_name: firstName,
        last_name: lastName,
      });
      toast({ title: t("profileUpdatedSuccess") });
    } catch {
      toast({ title: t("profileUpdateFailed"), variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleCreateApiKey = async () => {
    if (!newKeyName.trim()) return;
    setCreatingKey(true);
    try {
      const response = await api.post("/api-keys/", { name: newKeyName.trim() });
      const newKey = response.data;
      setApiKeys((prev) => [...prev, newKey]);
      setShowNewKey(newKey.key || null);
      setNewKeyName("");
      toast({ title: t("apiKeyCreatedSuccess") });
    } catch {
      toast({ title: t("apiKeyCreateFailed"), variant: "destructive" });
    } finally {
      setCreatingKey(false);
    }
  };

  const handleDeleteApiKey = async (keyId: string) => {
    try {
      await api.delete(`/api-keys/${keyId}/`);
      setApiKeys((prev) => prev.filter((k) => k.id !== keyId));
      toast({ title: t("apiKeyDeleted") });
    } catch {
      toast({ title: t("apiKeyDeleteFailed"), variant: "destructive" });
    }
  };

  const toggleKeyVisibility = (keyId: string) => {
    setShowKeys((prev) => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
        <p className="text-muted-foreground">
          {t("subtitle")}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-brand-teal/10 text-brand-teal shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Profile Tab */}
      {activeTab === "profile" && (
        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="username" className="text-sm font-medium">
              {t("username")}
            </label>
            <Input
              id="username"
              value={user?.username || ""}
              disabled
              className="max-w-md"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              {t("email")}
            </label>
            <Input
              id="email"
              value={user?.email || ""}
              disabled
              className="max-w-md"
            />
          </div>
          <div className="grid grid-cols-2 gap-4 max-w-md">
            <div className="space-y-2">
              <label htmlFor="firstName" className="text-sm font-medium">
                {t("firstName")}
              </label>
              <Input
                id="firstName"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="lastName" className="text-sm font-medium">
                {t("lastName")}
              </label>
              <Input
                id="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? t("saving") : t("saveChanges")}
          </Button>
        </div>
      )}

      {/* Appearance Tab */}
      {activeTab === "appearance" && (
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("theme")}</label>
            <div className="flex gap-2">
              {(["light", "dark", "system"] as const).map((v) => (
                <Button
                  key={v}
                  variant={theme === v ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTheme(v)}
                  className="capitalize"
                >
                  {t(v)}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* API Keys Tab */}
      {activeTab === "api-keys" && (
        <div className="space-y-4">
          {showNewKey && (
            <div className="rounded-md bg-green-50 p-3 text-sm dark:bg-green-900/20">
              <p className="font-medium text-green-800 dark:text-green-200">
                {t("newApiKeyCreated")}
              </p>
              <code className="mt-1 block break-all font-mono text-xs">
                {showNewKey}
              </code>
              <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                {t("copyKeyWarning")}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => setShowNewKey(null)}
              >
                {tc("dismiss")}
              </Button>
            </div>
          )}

          {apiKeys.length > 0 ? (
            <div className="space-y-2">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between rounded-md border p-3"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium">{key.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {showKeys[key.id] ? key.key_preview : "••••••••••••••••"}
                      {" "}
                      {t("createdLabel", { date: new Date(key.created_at).toLocaleDateString() })}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => toggleKeyVisibility(key.id)}
                    >
                      {showKeys[key.id] ? (
                        <EyeOff className="h-3.5 w-3.5" />
                      ) : (
                        <Eye className="h-3.5 w-3.5" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => handleDeleteApiKey(key.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              {t("noApiKeys")}
            </p>
          )}

          <div className="flex items-center gap-2">
            <Input
              placeholder={t("keyNamePlaceholder")}
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              className="max-w-sm"
              onKeyDown={(e) => e.key === "Enter" && handleCreateApiKey()}
            />
            <Button
              onClick={handleCreateApiKey}
              disabled={creatingKey || !newKeyName.trim()}
              size="sm"
            >
              <Plus className="mr-1 h-3.5 w-3.5" />
              {creatingKey ? t("creating") : t("createKey")}
            </Button>
          </div>
        </div>
      )}

      {/* AI Providers Tab */}
      {activeTab === "ai-providers" && <AIProviders />}

      {/* Organization Tab */}
      {activeTab === "organization" && <OrganizationSettings />}
    </div>
  );
}
