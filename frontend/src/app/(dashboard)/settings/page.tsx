"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api";
import AIProviders from "@/components/features/settings/ai-providers";
import { Trash2, Plus, Eye, EyeOff } from "lucide-react";

interface ApiKey {
  id: string;
  name: string;
  key_preview: string;
  created_at: string;
  last_used: string | null;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, setTheme } = useUIStore();
  const { toast } = useToast();
  const [firstName, setFirstName] = useState(user?.first_name || "");
  const [lastName, setLastName] = useState(user?.last_name || "");
  const [saving, setSaving] = useState(false);

  // API Key management state
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
      toast({ title: "Profile updated successfully" });
    } catch {
      toast({ title: "Failed to update profile", variant: "destructive" });
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
      toast({ title: "API key created successfully" });
    } catch {
      toast({ title: "Failed to create API key", variant: "destructive" });
    } finally {
      setCreatingKey(false);
    }
  };

  const handleDeleteApiKey = async (keyId: string) => {
    try {
      await api.delete(`/api-keys/${keyId}/`);
      setApiKeys((prev) => prev.filter((k) => k.id !== keyId));
      toast({ title: "API key deleted" });
    } catch {
      toast({ title: "Failed to delete API key", variant: "destructive" });
    }
  };

  const toggleKeyVisibility = (keyId: string) => {
    setShowKeys((prev) => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Update your personal information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium">
                Username
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
                Email
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
                  First Name
                </label>
                <Input
                  id="firstName"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="lastName" className="text-sm font-medium">
                  Last Name
                </label>
                <Input
                  id="lastName"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            </div>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>
              Customize the look and feel of the application
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Theme</label>
              <div className="flex gap-2">
                {(["light", "dark", "system"] as const).map((t) => (
                  <Button
                    key={t}
                    variant={theme === t ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTheme(t)}
                    className="capitalize"
                  >
                    {t}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>API Keys</CardTitle>
            <CardDescription>
              Manage your API keys for programmatic access
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {showNewKey && (
              <div className="rounded-md bg-green-50 p-3 text-sm dark:bg-green-900/20">
                <p className="font-medium text-green-800 dark:text-green-200">
                  New API Key Created
                </p>
                <code className="mt-1 block break-all font-mono text-xs">
                  {showNewKey}
                </code>
                <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                  Copy this key now. It will not be shown again.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => setShowNewKey(null)}
                >
                  Dismiss
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
                        Created: {new Date(key.created_at).toLocaleDateString()}
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
                No API keys created yet.
              </p>
            )}

            <div className="flex items-center gap-2">
              <Input
                placeholder="Key name (e.g., CI/CD Pipeline)"
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
                {creatingKey ? "Creating..." : "Create Key"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <AIProviders />
      </div>
    </div>
  );
}
