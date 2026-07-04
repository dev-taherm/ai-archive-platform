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

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, setTheme } = useUIStore();
  const { toast } = useToast();
  const [firstName, setFirstName] = useState(user?.first_name || "");
  const [lastName, setLastName] = useState(user?.last_name || "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/auth/users/${user?.id}/`, {
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
          <CardContent>
            <p className="text-sm text-muted-foreground">
              API key management coming soon.
            </p>
          </CardContent>
        </Card>

        <AIProviders />
      </div>
    </div>
  );
}
