"use client";

import type { FileRecord } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MoreVertical, FolderOpen, Loader2, FileIcon, FileImage, FileSpreadsheet, FileCode } from "lucide-react";
import { formatBytes, formatDateTime } from "@/lib/utils";

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith("image/")) return FileImage;
  if (mimeType.includes("spreadsheet") || mimeType.includes("excel")) return FileSpreadsheet;
  if (mimeType.includes("pdf")) return FileIcon;
  if (mimeType.includes("code") || mimeType.includes("json") || mimeType.includes("xml")) return FileCode;
  return FileIcon;
}

function getStatusColor(status: string) {
  switch (status) {
    case "completed": return "success" as const;
    case "failed": return "destructive" as const;
    case "indexing": return "warning" as const;
    default: return "secondary" as const;
  }
}

interface FilesTableProps {
  files: FileRecord[];
  onAction: (action: string, file: FileRecord) => void;
  processingId: string | null;
  actionMenu: string | null;
  onToggleMenu: (fileId: string) => void;
  t: Function;
  tc: Function;
}

export default function FilesTable({
  files,
  onAction,
  processingId,
  actionMenu,
  onToggleMenu,
  t,
  tc,
}: FilesTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("file")}</TableHead>
          <TableHead>{t("type")}</TableHead>
          <TableHead>{t("size")}</TableHead>
          <TableHead>{t("status")}</TableHead>
          <TableHead>{t("tags")}</TableHead>
          <TableHead>{t("added")}</TableHead>
          <TableHead className="w-10"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {files.map((file) => {
          const Icon = getFileIcon(file.mime_type);
          return (
            <TableRow key={file.id}>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="max-w-[300px] truncate text-sm font-medium">
                    {file.path.split("/").pop()}
                  </span>
                </div>
                <p className="max-w-[300px] truncate text-xs text-muted-foreground">
                  {file.path}
                </p>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {file.mime_type.split("/").pop()}
              </TableCell>
              <TableCell className="text-sm">
                {formatBytes(file.size_bytes)}
              </TableCell>
              <TableCell>
                <Badge variant={getStatusColor(file.status)}>
                  {file.status}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex gap-1 flex-wrap">
                  {file.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {file.tags.length > 3 && (
                    <Badge variant="outline" className="text-xs">
                      +{file.tags.length - 3}
                    </Badge>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDateTime(file.created_at)}
              </TableCell>
              <TableCell>
                <div className="relative">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => onToggleMenu(file.id)}
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                  {actionMenu === file.id && (
                    <div className="absolute right-0 top-8 z-50 w-48 rounded-md border bg-popover p-1 shadow-md">
                      <button
                        className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                        onClick={() => onAction("process", file)}
                        disabled={processingId === file.id}
                      >
                        {processingId === file.id ? (
                          <Loader2 className="h-4 w-4 animate-spin text-brand-teal" />
                        ) : (
                          <span className="h-4 w-4" />
                        )}
                        {processingId === file.id ? t("processing") : t("processDocument")}
                      </button>
                      <button
                        className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                        onClick={() => onAction("move", file)}
                      >
                        <span className="h-4 w-4" />
                        {t("moveFile")}
                      </button>
                      <button
                        className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-muted"
                        onClick={() => onAction("delete", file)}
                      >
                        <span className="h-4 w-4" />
                        {tc("delete")}
                      </button>
                    </div>
                  )}
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
