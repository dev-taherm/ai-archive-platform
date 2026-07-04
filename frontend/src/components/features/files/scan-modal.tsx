"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { ScanResult } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FolderSearch, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

interface ScanModalProps {
  onClose: () => void;
}

export function ScanModal({ onClose }: ScanModalProps) {
  const queryClient = useQueryClient();
  const [folderPath, setFolderPath] = useState("");
  const [recursive, setRecursive] = useState(true);
  const [result, setResult] = useState<ScanResult | null>(null);

  const scanMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<ScanResult>("/files/scan", {
        folder_path: folderPath,
        recursive,
      });
      return res.data;
    },
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["files"] });
    },
  });

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
                Scan a server directory to discover and index files
              </CardDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="folderPath" className="text-sm font-medium">
              Folder Path (server-side)
            </label>
            <Input
              id="folderPath"
              placeholder="/home/user/documents"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              disabled={scanMutation.isPending}
            />
            <p className="text-xs text-muted-foreground">
              Absolute path on the server filesystem
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="recursive"
              checked={recursive}
              onChange={(e) => setRecursive(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
              disabled={scanMutation.isPending}
            />
            <label htmlFor="recursive" className="text-sm">
              Scan subdirectories recursively
            </label>
          </div>

          {scanMutation.isError && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="mb-1 inline h-4 w-4" />
              {(scanMutation.error as any)?.response?.data?.detail || "Scan failed"}
            </div>
          )}

          {result && (
            <div className="rounded-md border bg-muted/50 p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-green-600">
                <CheckCircle className="h-4 w-4" />
                Scan Complete
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>Files found: <strong>{result.total_files_found}</strong></div>
                <div>Files scanned: <strong>{result.files_scanned}</strong></div>
                <div>New files: <strong>{result.new_files}</strong></div>
                <div>Skipped: <strong>{result.skipped_files}</strong></div>
                <div>Failed: <strong>{result.failed_files}</strong></div>
                <div>Duration: <strong>{result.scan_duration_seconds.toFixed(1)}s</strong></div>
              </div>
              {result.errors.length > 0 && (
                <div className="mt-2 text-xs text-destructive">
                  Errors: {result.errors.join("; ")}
                </div>
              )}
            </div>
          )}
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={scanMutation.isPending}>
            {result ? "Close" : "Cancel"}
          </Button>
          {!result && (
            <Button
              onClick={() => scanMutation.mutate()}
              disabled={!folderPath.trim() || scanMutation.isPending}
            >
              {scanMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                "Scan"
              )}
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
