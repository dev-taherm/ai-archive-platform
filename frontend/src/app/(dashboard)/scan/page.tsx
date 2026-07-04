"use client";

import { useState, useRef, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FolderSearch,
  FolderOpen,
  Play,
  FileIcon,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import api from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ScanResult, ScanProgressEvent } from "@/types/api";

export default function ScanPage() {
  const queryClient = useQueryClient();
  const [folderPath, setFolderPath] = useState("");
  const [recursive, setRecursive] = useState(true);
  const [patterns, setPatterns] = useState("");
  const [ignorePatterns, setIgnorePatterns] = useState("");
  const [progress, setProgress] = useState<ScanProgressEvent | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const scanMutation = useMutation({
    mutationFn: async (params: {
      folder_path: string;
      recursive: boolean;
      patterns?: string[];
      ignore_patterns?: string[];
    }) => {
      const res = await api.post<ScanResult>("/scan", params);
      return res.data;
    },
    onSuccess: (data) => {
      setResult(data);
      setProgress(null);
      queryClient.invalidateQueries({ queryKey: ["files"] });
    },
    onError: () => {
      setProgress(null);
    },
  });

  const handleScan = useCallback(() => {
    if (!folderPath.trim()) return;

    setResult(null);
    setProgress({ event: "scan_started", data: { message: "Starting scan..." } });

    const params: {
      folder_path: string;
      recursive: boolean;
      patterns?: string[];
      ignore_patterns?: string[];
    } = {
      folder_path: folderPath.trim(),
      recursive,
    };

    if (patterns.trim()) {
      params.patterns = patterns.split(",").map((p) => p.trim()).filter(Boolean);
    }
    if (ignorePatterns.trim()) {
      params.ignore_patterns = ignorePatterns.split(",").map((p) => p.trim()).filter(Boolean);
    }

    scanMutation.mutate(params);
  }, [folderPath, recursive, patterns, ignorePatterns, scanMutation]);

  const isScanning = scanMutation.isPending;

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
                />
              </div>
              <Button
                onClick={handleScan}
                disabled={!folderPath.trim() || isScanning}
              >
                {isScanning ? (
                  <>
                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Start Scan
                  </>
                )}
              </Button>
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

      {progress && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {isScanning && (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              )}
              Scan Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm">
                {progress.data.message || progress.data.current_file || "Processing..."}
              </p>
              {progress.data.processed != null && progress.data.total_found != null && (
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{progress.data.processed} / {progress.data.total_found} files</span>
                    <span>
                      {progress.data.total_found > 0
                        ? `${Math.round((progress.data.processed / progress.data.total_found) * 100)}%`
                        : "0%"}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{
                        width: `${
                          progress.data.total_found > 0
                            ? (progress.data.processed / progress.data.total_found) * 100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>
              )}
              {progress.data.new != null && (
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span className="text-emerald-600">{progress.data.new} new</span>
                  <span>{progress.data.skipped ?? 0} skipped</span>
                  {progress.data.failed != null && progress.data.failed > 0 && (
                    <span className="text-red-600">{progress.data.failed} failed</span>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-emerald-600" />
              Scan Complete
            </CardTitle>
            <CardDescription>
              Scanned {result.folder_path} in {result.scan_duration_seconds.toFixed(1)}s
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold">{result.total_files_found}</p>
                <p className="text-xs text-muted-foreground">Files Found</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold">{result.files_scanned}</p>
                <p className="text-xs text-muted-foreground">Scanned</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold text-emerald-600">{result.new_files}</p>
                <p className="text-xs text-muted-foreground">New Files</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold">{result.skipped_files}</p>
                <p className="text-xs text-muted-foreground">Skipped</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-2xl font-bold text-red-600">{result.failed_files}</p>
                <p className="text-xs text-muted-foreground">Failed</p>
              </div>
            </div>

            {result.errors.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
                <div className="flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-200">
                  <AlertTriangle className="h-4 w-4" />
                  Errors ({result.errors.length})
                </div>
                <ul className="mt-2 space-y-1 text-xs text-amber-700 dark:text-amber-300">
                  {result.errors.slice(0, 5).map((error, i) => (
                    <li key={i}>• {error}</li>
                  ))}
                  {result.errors.length > 5 && (
                    <li>• ...and {result.errors.length - 5} more</li>
                  )}
                </ul>
              </div>
            )}

            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>
                <Clock className="mr-1 inline h-3.5 w-3.5" />
                Scanned at: {formatDateTime(result.scanned_at)}
              </span>
              {result.file_ids.length > 0 && (
                <Button
                  variant="link"
                  className="h-auto p-0"
                  onClick={() => queryClient.invalidateQueries({ queryKey: ["files"] })}
                >
                  View {result.file_ids.length} files
                  <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {scanMutation.isError && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-4">
            <XCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="text-sm font-medium text-destructive">Scan failed</p>
              <p className="text-xs text-muted-foreground">
                {scanMutation.error?.message || "An unexpected error occurred. Please try again."}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
