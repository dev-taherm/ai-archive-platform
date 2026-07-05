"use client";

import { useState, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth-store";
import api from "@/lib/api";
import {
  FolderSearch,
  FolderOpen,
  Play,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Clock,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type ScanPhase = "idle" | "scanning" | "complete" | "error";

interface ScanState {
  phase: ScanPhase;
  processed: number;
  totalFound: number;
  newFiles: number;
  skipped: number;
  failed: number;
  currentFile: string;
  errors: string[];
  errorMessage: string;
  scanDuration: number;
}

const initialState: ScanState = {
  phase: "idle",
  processed: 0,
  totalFound: 0,
  newFiles: 0,
  skipped: 0,
  failed: 0,
  currentFile: "",
  errors: [],
  errorMessage: "",
  scanDuration: 0,
};

export default function ScanPage() {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [folderPath, setFolderPath] = useState("");
  const [recursive, setRecursive] = useState(true);
  const [patterns, setPatterns] = useState("");
  const [ignorePatterns, setIgnorePatterns] = useState("");
  const [state, setState] = useState<ScanState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  const handleSSEvent = useCallback((eventName: string, dataStr: string) => {
    try {
      const data = JSON.parse(dataStr);

      switch (eventName) {
        case "scan_started":
          setState((s) => ({
            ...s,
            currentFile: data.message || "Scanning...",
          }));
          break;

        case "file_scanned":
          setState((s) => ({
            ...s,
            processed: data.processed ?? s.processed,
            totalFound: data.total_found ?? s.totalFound,
            currentFile: data.current_file ?? s.currentFile,
            newFiles: data.new ?? s.newFiles,
            skipped: data.skipped ?? s.skipped,
            failed: data.failed ?? s.failed,
          }));
          break;

        case "scan_complete":
          setState((s) => ({
            ...s,
            phase: "complete",
            processed: data.files_scanned ?? s.processed,
            totalFound: data.total_found ?? s.totalFound,
            newFiles: data.new_files ?? s.newFiles,
            skipped: data.skipped_files ?? s.skipped,
            failed: data.failed_files ?? s.failed,
            errors: data.errors ?? [],
            scanDuration: data.scan_duration_seconds ?? 0,
            currentFile: "",
          }));
          queryClient.invalidateQueries({ queryKey: ["files"] });
          break;

        case "scan_error":
          setState((s) => ({
            ...s,
            phase: "error",
            errorMessage: data.detail || "Scan failed unexpectedly.",
          }));
          break;
      }
    } catch {}
  }, [queryClient]);

  const handleScan = useCallback(async () => {
    const trimmedPath = folderPath.trim();
    if (!trimmedPath) return;

    setState({ ...initialState, phase: "scanning", currentFile: "Starting scan..." });

    if (!accessToken) {
      setState((s) => ({
        ...s,
        phase: "error",
        errorMessage: "Session expired — please log in again.",
      }));
      return;
    }

    // Pre-refresh token via axios interceptor before opening SSE stream
    try {
      await api.get("/users/me");
    } catch {
      // If refresh fails, the interceptor will redirect to login
    }
    const freshToken = useAuthStore.getState().accessToken;
    if (!freshToken) {
      setState((s) => ({
        ...s,
        phase: "error",
        errorMessage: "Session expired — please log in again.",
      }));
      return;
    }

    const params = new URLSearchParams({
      folder_path: trimmedPath,
      recursive: String(recursive),
    });
    if (patterns.trim()) {
      // scan-stream doesn't support patterns yet, but pass as query param for future use
    }
    if (ignorePatterns.trim()) {
      // scan-stream doesn't support ignore_patterns yet, but pass as query param for future use
    }

    const abortController = new AbortController();
    abortRef.current = abortController;

    try {
      const response = await fetch(`/api/v1/files/scan-stream?${params.toString()}`, {
        headers: { Authorization: `Bearer ${freshToken}` },
        signal: abortController.signal,
      });

      if (!response.ok) {
        if (response.status === 401) {
          setState((s) => ({
            ...s,
            phase: "error",
            errorMessage: "Session expired — please log in again.",
          }));
          return;
        }
        let detail = `Scan failed (HTTP ${response.status})`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch {}
        setState((s) => ({ ...s, phase: "error", errorMessage: detail }));
        return;
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7);
          } else if (line.startsWith("data: ")) {
            currentData = line.slice(6);
          } else if (line === "" && currentEvent && currentData) {
            handleSSEvent(currentEvent, currentData);
            currentEvent = "";
            currentData = "";
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        setState(initialState);
      } else {
        setState((s) => ({
          ...s,
          phase: "error",
          errorMessage: err.message || "Network error — could not connect to scan endpoint.",
        }));
      }
    } finally {
      abortRef.current = null;
    }
  }, [folderPath, recursive, patterns, ignorePatterns, accessToken, handleSSEvent]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    setState(initialState);
  }, []);

  const isScanning = state.phase === "scanning";
  const isComplete = state.phase === "complete";
  const isError = state.phase === "error";
  const isIdle = state.phase === "idle";

  const progressPercent =
    state.totalFound > 0 ? Math.min((state.processed / state.totalFound) * 100, 100) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Scan Folder</h1>
        <p className="text-muted-foreground">
          Scan a directory to discover and index files
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Scan Configuration</CardTitle>
          <CardDescription>
            Specify the folder path and options for the scan
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="folderPath" className="text-sm font-medium">
              Folder Path
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <FolderOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="folderPath"
                  placeholder="/path/to/folder"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  className="pl-10"
                  disabled={isScanning}
                  onKeyDown={(e) => e.key === "Enter" && !isScanning && folderPath.trim() && handleScan()}
                />
              </div>
              {isIdle ? (
                <Button
                  onClick={handleScan}
                  disabled={!folderPath.trim()}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Start Scan
                </Button>
              ) : isScanning ? (
                <Button variant="destructive" onClick={handleCancel}>
                  Cancel
                </Button>
              ) : (
                <Button onClick={() => { setState(initialState); setFolderPath(""); }}>
                  Scan Again
                </Button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                disabled={isScanning}
                className="h-4 w-4 rounded border-gray-300"
              />
              Scan recursively
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="patterns" className="text-sm font-medium">
                Include Patterns
              </label>
              <Input
                id="patterns"
                placeholder="*.pdf, *.docx, *.txt"
                value={patterns}
                onChange={(e) => setPatterns(e.target.value)}
                disabled={isScanning}
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated glob patterns
              </p>
            </div>
            <div className="space-y-2">
              <label htmlFor="ignorePatterns" className="text-sm font-medium">
                Ignore Patterns
              </label>
              <Input
                id="ignorePatterns"
                placeholder="node_modules, .git"
                value={ignorePatterns}
                onChange={(e) => setIgnorePatterns(e.target.value)}
                disabled={isScanning}
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated patterns to skip
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress section — shown during scan */}
      {isScanning && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Scan Progress
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Progress value={progressPercent} />

            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">Found:</span>
                <span className="font-mono font-medium">{state.totalFound}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">Processed:</span>
                <span className="font-mono font-medium">{state.processed}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-green-600 dark:text-green-400">New:</span>
                <span className="font-mono font-medium text-green-600 dark:text-green-400">
                  {state.newFiles}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-amber-600 dark:text-amber-400">Skipped:</span>
                <span className="font-mono font-medium text-amber-600 dark:text-amber-400">
                  {state.skipped}
                </span>
              </div>
              {state.failed > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-destructive">Failed:</span>
                  <span className="font-mono font-medium text-destructive">
                    {state.failed}
                  </span>
                </div>
              )}
            </div>

            {state.currentFile && (
              <p className="truncate text-xs text-muted-foreground" title={state.currentFile}>
                {state.currentFile}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Results — shown after scan completes */}
      {isComplete && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-emerald-600" />
              Scan Complete
            </CardTitle>
            <CardDescription>
              Scanned {folderPath.trim()} in {state.scanDuration.toFixed(1)}s
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold">{state.totalFound}</p>
                <p className="text-xs text-muted-foreground">Files Found</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold">{state.processed}</p>
                <p className="text-xs text-muted-foreground">Scanned</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold text-emerald-600">{state.newFiles}</p>
                <p className="text-xs text-muted-foreground">New Files</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold">{state.skipped}</p>
                <p className="text-xs text-muted-foreground">Skipped</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold text-red-600">{state.failed}</p>
                <p className="text-xs text-muted-foreground">Failed</p>
              </div>
            </div>

            {state.errors.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
                <div className="flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-200">
                  <AlertTriangle className="h-4 w-4" />
                  Errors ({state.errors.length})
                </div>
                <ul className="mt-2 space-y-1 text-xs text-amber-700 dark:text-amber-300">
                  {state.errors.slice(0, 5).map((error, i) => (
                    <li key={i}>• {error}</li>
                  ))}
                  {state.errors.length > 5 && (
                    <li>• ...and {state.errors.length - 5} more</li>
                  )}
                </ul>
              </div>
            )}

            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>
                <Clock className="mr-1 inline h-3.5 w-3.5" />
                Duration: {state.scanDuration.toFixed(1)}s
              </span>
              {state.newFiles > 0 && (
                <Button
                  variant="link"
                  className="h-auto p-0"
                  onClick={() => queryClient.invalidateQueries({ queryKey: ["files"] })}
                >
                  View {state.newFiles} new files
                  <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error state */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="text-sm font-medium text-destructive">Scan failed</p>
              <p className="text-xs text-muted-foreground">
                {state.errorMessage}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
