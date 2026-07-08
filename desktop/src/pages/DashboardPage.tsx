import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../stores/auth-store";
import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { LanguageSwitcher } from "../components/LanguageSwitcher";

interface AgentStatus {
  running: boolean;
  port: number;
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);

  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkStatus = async () => {
    try {
      const resp = await fetch("http://localhost:8420/api/health");
      if (resp.ok) {
        setStatus({ running: true, port: 8420 });
      } else {
        setStatus({ running: false, port: 8420 });
      }
    } catch {
      setStatus({ running: false, port: 8420 });
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      await fetch("http://localhost:8420/api/watch/start", { method: "POST" });
      setTimeout(checkStatus, 1000);
    } catch {
      // Agent not running
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="border-b bg-background px-6 py-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t("dashboard.title")}</h1>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <Button variant="ghost" size="sm" onClick={() => navigate("/settings")}>
            {t("dashboard.viewSettings")}
          </Button>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            {t("common.logout")}
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t("dashboard.agentStatus")}</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-muted-foreground">{t("common.loading")}</p>
            ) : (
              <div className="flex items-center gap-4">
                <Badge variant={status?.running ? "success" : "destructive"}>
                  {status?.running ? t("dashboard.running") : t("dashboard.stopped")}
                </Badge>
                {status?.running ? (
                  <Button variant="outline" size="sm">
                    {t("dashboard.stop")}
                  </Button>
                ) : (
                  <Button variant="outline" size="sm" onClick={handleStart}>
                    {t("dashboard.start")}
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="cursor-pointer hover:border-primary/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-base">{t("dashboard.scanFolder")}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="cursor-pointer hover:border-primary/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-base">{t("dashboard.syncNow")}</CardTitle>
            </CardHeader>
          </Card>
          <Card
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => navigate("/settings")}
          >
            <CardHeader>
              <CardTitle className="text-base">{t("dashboard.viewSettings")}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{t("dashboard.recentFiles")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{t("dashboard.noFiles")}</p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
