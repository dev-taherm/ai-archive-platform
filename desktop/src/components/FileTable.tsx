import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Scan, Loader2, Check, Pencil, Trash2, Move } from "lucide-react";
import type { FileRecord } from "../stores/agent-store";
import { useAgentStore } from "../stores/agent-store";

interface FileTableProps {
  files: FileRecord[];
  selectedFiles: Set<string>;
  processingFiles: Set<string>;
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onScanFile: (id: string) => void;
  onScanSelected: () => void;
}

function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(iso: string): string {
  if (!iso) return "\u2014";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

const statusVariant: Record<string, "success" | "destructive" | "default" | "secondary"> = {
  completed: "success",
  processed: "success",
  failed: "destructive",
  processing: "default",
  pending: "secondary",
};

export function FileTable({
  files, selectedFiles, processingFiles,
  onToggleSelect, onSelectAll, onClearSelection,
  onScanFile, onScanSelected,
}: FileTableProps) {
  const { t } = useTranslation();
  const { renameFile, deleteFile, moveFile } = useAgentStore();
  const allSelected = files.length > 0 && selectedFiles.size === files.length;
  const hasSelection = selectedFiles.size > 0;
  const pendingFiles = files.filter(f => f.processing_status === "pending" || f.processing_status === "failed");

  const handleRename = (file: FileRecord) => {
    const newName = window.prompt("New filename:", file.filename);
    if (newName && newName !== file.filename) {
      renameFile(file.id, newName);
    }
  };

  const handleMove = (file: FileRecord) => {
    const destDir = window.prompt("Destination directory (full path):");
    if (destDir) {
      const destPath = destDir.endsWith("/") ? destDir + file.filename : destDir + "/" + file.filename;
      moveFile(file.id, destPath);
    }
  };

  const handleDelete = (file: FileRecord) => {
    if (window.confirm(`Move "${file.filename}" to trash?`)) {
      deleteFile(file.id);
    }
  };

  if (files.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          {t("files.empty")}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">{t("files.title")}</CardTitle>
        {hasSelection && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selectedFiles.size} selected
            </span>
            <Button variant="outline" size="sm" onClick={onClearSelection}>
              {t("files.clear") || "Clear"}
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={onScanSelected}
            >
              <Scan className="h-4 w-4 mr-1" />
              Scan Selected ({selectedFiles.size})
            </Button>
          </div>
        )}
        {!hasSelection && pendingFiles.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={onSelectAll}
          >
            <Scan className="h-4 w-4 mr-1" />
            Scan All ({pendingFiles.length})
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-2 w-8">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={() => allSelected ? onClearSelection() : onSelectAll()}
                    className="rounded border-gray-300"
                  />
                </th>
                <th className="pb-2 font-medium">{t("files.name")}</th>
                <th className="pb-2 font-medium">{t("files.size")}</th>
                <th className="pb-2 font-medium">{t("files.status")}</th>
                <th className="pb-2 font-medium">{t("files.synced")}</th>
                <th className="pb-2 font-medium">{t("files.added")}</th>
                <th className="pb-2 font-medium w-32">{t("files.actions") || "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => {
                const isProcessing = processingFiles.has(file.id);
                const isPending = file.processing_status === "pending";
                const isFailed = file.processing_status === "failed";
                const canScan = (isPending || isFailed) && !isProcessing;

                return (
                  <tr key={file.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-2 pr-2">
                      <input
                        type="checkbox"
                        checked={selectedFiles.has(file.id)}
                        onChange={() => onToggleSelect(file.id)}
                        disabled={isProcessing}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="py-2 max-w-[200px] truncate" title={file.local_path}>
                      {file.filename}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {formatSize(file.size_bytes)}
                    </td>
                    <td className="py-2">
                      <Badge variant={statusVariant[file.processing_status] || "default"}>
                        {isProcessing ? "scanning..." : file.processing_status}
                      </Badge>
                    </td>
                    <td className="py-2">
                      {file.synced ? (
                        <Badge variant="success">{t("files.yes")}</Badge>
                      ) : (
                        <Badge variant="secondary">{t("files.no")}</Badge>
                      )}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {formatDate(file.first_seen_at)}
                    </td>
                    <td className="py-2">
                      <div className="flex items-center gap-1">
                        {isProcessing ? (
                          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                        ) : canScan ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onScanFile(file.id)}
                            title="Scan this file"
                          >
                            <Scan className="h-4 w-4" />
                          </Button>
                        ) : file.processing_status === "completed" ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : null}
                        <Button variant="ghost" size="sm" onClick={() => handleRename(file)} title="Rename">
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleMove(file)} title="Move">
                          <Move className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(file)} title="Delete">
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
