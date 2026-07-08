import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useConfigStore } from "../stores/config-store";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { LanguageSwitcher } from "../components/LanguageSwitcher";

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { serverUrl, apiKey, agentName, folders, setConfig } = useConfigStore();

  const [localServerUrl, setLocalServerUrl] = useState(serverUrl);
  const [localApiKey, setLocalApiKey] = useState(apiKey);
  const [localAgentName, setLocalAgentName] = useState(agentName);
  const [newFolder, setNewFolder] = useState("");
  const [localFolders, setLocalFolders] = useState<string[]>(folders);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setConfig({
      serverUrl: localServerUrl,
      apiKey: localApiKey,
      agentName: localAgentName,
      folders: localFolders,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleAddFolder = () => {
    if (newFolder.trim() && !localFolders.includes(newFolder.trim())) {
      setLocalFolders([...localFolders, newFolder.trim()]);
      setNewFolder("");
    }
  };

  const handleRemoveFolder = (folder: string) => {
    setLocalFolders(localFolders.filter((f) => f !== folder));
  };

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="border-b bg-background px-6 py-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t("settings.title")}</h1>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
            ← {t("dashboard.title")}
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-2xl p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.general")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("settings.agentName")}</label>
              <Input
                placeholder={t("settings.agentNamePlaceholder")}
                value={localAgentName}
                onChange={(e) => setLocalAgentName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("settings.language")}</label>
              <div className="flex gap-2">
                <Button
                  variant={i18n.language === "en" ? "default" : "outline"}
                  size="sm"
                  onClick={() => i18n.changeLanguage("en")}
                >
                  English
                </Button>
                <Button
                  variant={i18n.language === "ar" ? "default" : "outline"}
                  size="sm"
                  onClick={() => i18n.changeLanguage("ar")}
                >
                  العربية
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.server")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("settings.serverUrl")}</label>
              <Input
                type="url"
                placeholder="https://app.basirah.com"
                value={localServerUrl}
                onChange={(e) => setLocalServerUrl(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("settings.apiKey")}</label>
              <Input
                type="text"
                placeholder="your-api-key"
                value={localApiKey}
                onChange={(e) => setLocalApiKey(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.folders")}</CardTitle>
            <CardDescription>
              {localFolders.length} folder(s) configured
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="/path/to/folder"
                value={newFolder}
                onChange={(e) => setNewFolder(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddFolder()}
              />
              <Button variant="outline" onClick={handleAddFolder}>
                {t("settings.addFolder")}
              </Button>
            </div>
            <div className="space-y-2">
              {localFolders.map((folder) => (
                <div key={folder} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span className="text-sm font-mono">{folder}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveFolder(folder)}
                  >
                    {t("common.delete")}
                  </Button>
                </div>
              ))}
              {localFolders.length === 0 && (
                <p className="text-sm text-muted-foreground">No folders added yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-2">
          {saved && (
            <p className="text-sm text-green-600 self-center">{t("settings.saved")}</p>
          )}
          <Button onClick={handleSave}>{t("settings.save")}</Button>
        </div>
      </main>
    </div>
  );
}
