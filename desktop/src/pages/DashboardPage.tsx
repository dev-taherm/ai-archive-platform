import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAgentStore } from "../stores/agent-store";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { StatsCards } from "../components/StatsCards";
import { FileTable } from "../components/FileTable";
import { ScanButton } from "../components/ScanButton";
import { Button } from "../components/ui/button";
import { Play, Square, RefreshCw, AlertCircle } from "lucide-react";

export default function DashboardPage() {
  const { t } = useTranslation();
  const {
    connected,
    status,
    files,
    loading,
    error,
    fetchStatus,
    fetchFiles,
    fetchLogs,
    fetchFolders,
    startWatcher,
    stopWatcher,
    syncNow,
    startAgent,
    stopAgent,
  } = useAgentStore();

  useEffect(() => {
    fetchStatus();
    fetchFiles();
    fetchFolders();
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
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={stopAgent}
                    disabled={loading}
                  >
                    <Square className="h-4 w-4 mr-1" />
                    Stop Agent
                  </Button>
                </>
              ) : (
                <Button
                  variant="default"
                  size="sm"
                  onClick={startAgent}
                  disabled={loading}
                >
                  <Play className="h-4 w-4 mr-1" />
                  Start Agent
                </Button>
              )}
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
        {/* <LogsViewer logs={logs.slice(-30)} /> */}
      </main>
    </div>
  );
}
