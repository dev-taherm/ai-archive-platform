import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAgentStore } from "../stores/agent-store";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { StatsCards } from "../components/StatsCards";
import { FileTable } from "../components/FileTable";
import { Button } from "../components/ui/button";
import { Play, Square, Pause, RefreshCw, AlertCircle } from "lucide-react";

export default function DashboardPage() {
  const { t } = useTranslation();
  const {
    connected, files, loading, error, paused, metrics,
    selectedFiles, processingFiles,
    fetchStatus, fetchFiles, fetchFolders, fetchMetrics,
    syncNow, startAgent, stopAgent,
    pauseAgent, resumeAgent,
    scanFile, scanSelected,
    toggleFileSelection, selectAllFiles, clearSelection,
  } = useAgentStore();

  useEffect(() => {
    fetchStatus();
    fetchFiles();
    fetchFolders();
    fetchMetrics();
    const interval = setInterval(() => {
      fetchStatus();
      fetchFiles();
      fetchMetrics();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const stats = {
    total: files.length,
    pending: files.filter(f => f.processing_status === "pending").length,
    completed: files.filter(f => f.processing_status === "completed").length,
    failed: files.filter(f => f.processing_status === "failed").length,
    synced: files.filter(f => f.synced).length,
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
              <Badge variant={connected ? (paused ? "secondary" : "success") : "destructive"}>
                {connected ? (paused ? "Paused" : t("dashboard.running")) : t("dashboard.stopped")}
              </Badge>
              <div className="flex-1" />
              {connected ? (
                <>
                  {paused ? (
                    <Button variant="outline" size="sm" onClick={resumeAgent} disabled={loading}>
                      <Play className="h-4 w-4 mr-1" />
                      Resume
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" onClick={pauseAgent} disabled={loading}>
                      <Pause className="h-4 w-4 mr-1" />
                      Pause
                    </Button>
                  )}
                  <Button variant="outline" size="sm" onClick={stopAgent} disabled={loading}>
                    <Square className="h-4 w-4 mr-1" />
                    Stop Agent
                  </Button>
                </>
              ) : (
                <Button variant="default" size="sm" onClick={startAgent} disabled={loading}>
                  <Play className="h-4 w-4 mr-1" />
                  Start Agent
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={() => syncNow()} disabled={loading || !connected}>
                <RefreshCw className="h-4 w-4 mr-1" />
                {t("dashboard.syncNow")}
              </Button>
            </div>

            {metrics && connected && (
              <div className="mt-3 grid grid-cols-3 gap-4 text-xs text-muted-foreground pt-3 border-t">
                <div>Scanned: {metrics.files_scanned}</div>
                <div>Errors: {metrics.parse_errors}</div>
                <div>Memory: {metrics.memory_mb?.toFixed(0) || "?"} MB</div>
              </div>
            )}
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

        {/* Files */}
        <FileTable
          files={files}
          selectedFiles={selectedFiles}
          processingFiles={processingFiles}
          onToggleSelect={toggleFileSelection}
          onSelectAll={selectAllFiles}
          onClearSelection={clearSelection}
          onScanFile={scanFile}
          onScanSelected={scanSelected}
        />
      </main>
    </div>
  );
}
