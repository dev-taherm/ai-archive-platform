import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAgentStore } from "../stores/agent-store";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { StatsCards } from "../components/StatsCards";
import { FileTable } from "../components/FileTable";
import { LogsViewer } from "../components/LogsViewer";
import { ScanButton } from "../components/ScanButton";
import { Button } from "../components/ui/button";
import { Play, Square, RefreshCw } from "lucide-react";

export default function DashboardPage() {
  const { t } = useTranslation();
  const {
    connected,
    status,
    files,
    logs,
    loading,
    fetchStatus,
    fetchFiles,
    fetchLogs,
    startWatcher,
    stopWatcher,
    syncNow,
  } = useAgentStore();

  useEffect(() => {
    fetchStatus();
    fetchFiles();
    fetchLogs(50);
    const interval = setInterval(() => {
      fetchStatus();
      fetchFiles();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const stats = status?.stats || {
    total: 0,
    synced: 0,
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  };

  return (
    <div className="min-h-full bg-muted/40">
      <div className="border-b bg-background px-6 py-3">
        <h1 className="text-lg font-semibold">{t("dashboard.title")}</h1>
      </div>

      <main className="mx-auto max-w-6xl p-6 space-y-6">
        {/* Agent Status */}
        <Card>
          <CardHeader>
            <CardTitle>{t("dashboard.agentStatus")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 flex-wrap">
              <Badge variant={connected ? "success" : "destructive"}>
                {connected ? t("dashboard.running") : t("dashboard.stopped")}
              </Badge>
              {status && (
                <span className="text-sm text-muted-foreground">
                  v{status.version} — uptime {Math.floor(status.uptime_seconds / 60)}m
                </span>
              )}
              <div className="flex-1" />
              {connected ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={stopWatcher}
                    disabled={loading}
                  >
                    <Square className="h-4 w-4 mr-1" />
                    {t("dashboard.stop")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => startWatcher()}
                    disabled={loading}
                  >
                    <Play className="h-4 w-4 mr-1" />
                    {t("dashboard.start")}
                  </Button>
                </>
              ) : null}
              <ScanButton />
              <Button
                variant="outline"
                size="sm"
                onClick={() => syncNow()}
                disabled={loading || !connected}
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                {t("dashboard.syncNow")}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <StatsCards
          total={stats.total}
          completed={stats.completed}
          synced={stats.synced}
          pending={stats.pending}
          failed={stats.failed}
        />

        {/* Recent Files */}
        <FileTable files={files.slice(0, 10)} />

        {/* Logs */}
        <LogsViewer logs={logs.slice(-30)} />
      </main>
    </div>
  );
}
