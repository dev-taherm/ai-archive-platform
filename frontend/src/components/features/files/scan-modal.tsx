"use client";

import { useState, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth-store";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  FolderSearch,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  FolderOpen,
} from "lucide-react";
import type { ScanProgressEvent } from "@/types/api";

interface ScanModalProps {
  onClose: () => void;
}

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
};

export function ScanModal({ onClose }: ScanModalProps) {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [folderPath, setFolderPath] = useState("");
  const [recursive, setRecursive] = useState(true);
  const [state, setState] = useState<ScanState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  const validatePath = (path: string): string | null => {
    const trimmed = path.trim();
    if (!trimmed) return "Folder path is required.";
    if (!trimmed.startsWith("/")) return "Folder path must be absolute (start with /).";
    if (/[/\\]$/.test(trimmed)) return "Folder path should not end with / or \\.";
    if (/\s/.test(trimmed)) return "Folder path must not contain spaces.";
    return null;
  };

  const handleScan = useCallback(async () => {
    const validationError = validatePath(folderPath);
    if (validationError) {
      setState((s) => ({ ...s, phase: "error", errorMessage: validationError }));
      return;
    }

    if (!accessToken) {
      setState((s) => ({
        ...s,
        phase: "error",
        errorMessage: "Session expired — please log in again.",
      }));
      return;
    }

    const trimmedPath = folderPath.trim();
    setState({ ...initialState, phase: "scanning", currentFile: "Starting scan..." });

    // Pre-refresh token via axios interceptor before opening SSE stream
    try {
      await api.get("/auth/me");
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
        setState((s) => ({ ...s, phase: "idle", currentFile: "" }));
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
  }, [folderPath, recursive, accessToken, queryClient]);

  const handleSSEvent = (eventName: string, dataStr: string) => {
    try {
      const data: ScanProgressEvent["data"] = JSON.parse(dataStr);

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
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    setState(initialState);
  };

  const progressPercent =
    state.totalFound > 0 ? Math.min((state.processed / state.totalFound) * 100, 100) : 0;

  const isScanning = state.phase === "scanning";
  const isComplete = state.phase === "complete";
  const isError = state.phase === "error";
  const isIdle = state.phase === "idle";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FolderSearch className="h-5 w-5" />
                Scan Folder
              </CardTitle>
              <CardDescription>
                Scan a server folder and index new documents
              </CardDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={isScanning ? handleCancel : onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Folder path input */}
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="folder-path">
              Folder Path
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <FolderOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="folder-path"
                  placeholder="/path/to/folder"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  disabled={isScanning}
                  className="pl-9 font-mono text-sm"
                  onKeyDown={(e) => e.key === "Enter" && !isScanning && handleScan()}
                />
              </div>
            </div>
          </div>

          {/* Recursive toggle */}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={recursive}
              onChange={(e) => setRecursive(e.target.checked)}
              disabled={isScanning}
              className="h-4 w-4 rounded border-gray-300"
            />
            Scan subfolders recursively
          </label>

          {/* Progress section — shown during and after scan */}
          {(isScanning || isComplete) && (
            <div className="space-y-3 rounded-lg border p-4">
              {/* Progress bar */}
              <Progress
                value={isComplete ? 100 : progressPercent}
                className={isComplete ? "[&>div]:bg-green-500" : ""}
              />

              {/* Counters */}
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

              {/* Current file */}
              {isScanning && state.currentFile && (
                <p className="truncate text-xs text-muted-foreground" title={state.currentFile}>
                  {state.currentFile}
                </p>
              )}

              {/* Completion message */}
              {isComplete && (
                <p className="text-sm font-medium text-green-600 dark:text-green-400">
                  Scan complete in {state.totalFound > 0 ? "" : "0s"}
                  {state.totalFound > 0 &&
                    ` ${state.processed} files processed — ${state.newFiles} new, ${state.skipped} skipped`}
                </p>
              )}

              {/* Errors during scan */}
              {state.errors.length > 0 && (
                <div className="space-y-1 rounded bg-destructive/10 p-2">
                  <p className="text-xs font-medium text-destructive">
                    {state.errors.length} error(s) during scan:
                  </p>
                  {state.errors.slice(0, 3).map((err, i) => (
                    <p key={i} className="truncate text-xs text-destructive/80" title={err}>
                      {err}
                    </p>
                  ))}
                  {state.errors.length > 3 && (
                    <p className="text-xs text-destructive/60">
                      +{state.errors.length - 3} more errors
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/5 p-4">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-destructive">Scan failed</p>
                <p className="text-sm text-destructive/80">{state.errorMessage}</p>
              </div>
            </div>
          )}

          {/* Idle validation hint */}
          {isIdle && folderPath && validatePath(folderPath) && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-500/50 bg-amber-500/5 p-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <p className="text-xs text-amber-600">{validatePath(folderPath)}</p>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-end gap-2">
          <Button variant="outline" onClick={isScanning ? handleCancel : onClose}>
            {isScanning ? "Cancel" : isComplete ? "Close" : "Cancel"}
          </Button>
          {isIdle && (
            <Button onClick={handleScan} disabled={!folderPath.trim()}>
              Start Scan
            </Button>
          )}
          {isComplete && (
            <Button
              onClick={() => {
                setState(initialState);
                setFolderPath("");
              }}
            >
              Scan Again
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
