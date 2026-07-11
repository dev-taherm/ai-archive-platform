import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { useConfigStore } from "../stores/config-store";
import { useAgentStore } from "../stores/agent-store";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "../components/ui/card";
import { LogsViewer } from "../components/LogsViewer";
import { Save } from "lucide-react";

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { serverUrl, apiKey, agentName, setConfig } = useConfigStore();
  const { logs, fetchLogs } = useAgentStore();

  const [localServerUrl, setLocalServerUrl] = useState(serverUrl);
  const [localApiKey, setLocalApiKey] = useState(apiKey);
  const [localAgentName, setLocalAgentName] = useState(agentName);
  const [ocrLang, setOcrLang] = useState("en");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    invoke<Record<string, string>>("get_config")
      .then((cfg) => {
        if (cfg.server_url) setLocalServerUrl(cfg.server_url);
        if (cfg.api_key) setLocalApiKey(cfg.api_key);
        if (cfg.agent_name) setLocalAgentName(cfg.agent_name);
        if (cfg.ocr_lang) setOcrLang(cfg.ocr_lang);
      })
      .catch(() => {});
    fetchLogs(200);
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      setConfig({
        serverUrl: localServerUrl,
        apiKey: localApiKey,
        agentName: localAgentName,
      });
      await invoke("update_config", {
        config: {
          server_url: localServerUrl,
          api_key: localApiKey,
          agent_name: localAgentName,
          ocr_lang: ocrLang,
        },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-full bg-muted/40">
      <div className="border-b bg-background px-6 py-3">
        <h1 className="text-lg font-semibold">{t("settings.title")}</h1>
      </div>

      <main className="mx-auto max-w-2xl p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.general")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.agentName")}
              </label>
              <Input
                placeholder={t("settings.agentNamePlaceholder")}
                value={localAgentName}
                onChange={(e) => setLocalAgentName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.language")}
              </label>
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
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.ocrLang")}
              </label>
              <Input
                value={ocrLang}
                onChange={(e) => setOcrLang(e.target.value)}
                placeholder="en"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.server")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.serverUrl")}
              </label>
              <Input
                type="url"
                placeholder="https://app.basirah.com"
                value={localServerUrl}
                onChange={(e) => setLocalServerUrl(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.apiKey")}
              </label>
              <Input
                type="text"
                placeholder="your-api-key"
                value={localApiKey}
                onChange={(e) => setLocalApiKey(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <LogsViewer logs={logs.slice(-50)} />

        <div className="flex justify-end gap-2">
          {saved && (
            <p className="text-sm text-green-600 self-center">
              {t("settings.saved")}
            </p>
          )}
          <Button onClick={handleSave} disabled={loading}>
            <Save className="h-4 w-4 mr-1" />
            {t("settings.save")}
          </Button>
        </div>
      </main>
    </div>
  );
}
