"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { FileRecord, ScanResult } from "@/types/api";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Search,
  Upload,
  FolderSearch,
  MoreVertical,
  Trash2,
  Play,
  FileIcon,
  FileImage,
  FileSpreadsheet,
  FileCode,
  RefreshCw,
  Download,
  Eye,
  X,
} from "lucide-react";
import { formatBytes, formatDateTime } from "@/lib/utils";
import { ScanModal } from "@/components/features/files/scan-modal";
import { UploadModal } from "@/components/features/files/upload-modal";

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

export default function FilesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showScan, setShowScan] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [actionMenu, setActionMenu] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<FileRecord | null>(null);

  const isPreviewable = (mime: string) =>
    mime.startsWith("image/") ||
    mime.startsWith("text/") ||
    mime === "application/pdf";

  const handleDownload = (fileId: string) => {
    const a = document.createElement("a");
    a.href = `/api/v1/files/${fileId}/download/`;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setActionMenu(null);
  };

  const { data: files = [], isLoading } = useQuery<FileRecord[]>({
    queryKey: ["files"],
    queryFn: async () => {
      const res = await api.get("/files");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/files/${id}/delete`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      setActionMenu(null);
    },
  });

  const processMutation = useMutation({
    mutationFn: async (fileId: string) => {
      const res = await api.post("/documents/process-pipeline", { file_id: fileId });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setActionMenu(null);
    },
  });

  const filtered = files.filter(
    (f) =>
      f.path.toLowerCase().includes(search.toLowerCase()) ||
      f.mime_type.toLowerCase().includes(search.toLowerCase()) ||
      f.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Files</h1>
          <p className="text-muted-foreground">
            Manage files on the server filesystem
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowScan(true)}>
            <FolderSearch className="mr-2 h-4 w-4" />
            Scan Folder
          </Button>
          <Button onClick={() => setShowUpload(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search files by name, type, or tag..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => queryClient.invalidateQueries({ queryKey: ["files"] })}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8 text-muted-foreground">
              Loading files...
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <FolderSearch className="mb-4 h-12 w-12 opacity-50" />
              <p className="text-lg font-medium">No files found</p>
              <p className="text-sm">
                {search ? "Try a different search term" : "Scan a folder or upload files to get started"}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Added</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((file) => {
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
                            onClick={() => setActionMenu(actionMenu === file.id ? null : file.id)}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                          {actionMenu === file.id && (
                            <div className="absolute right-0 top-8 z-50 w-48 rounded-md border bg-popover p-1 shadow-md">
                              {isPreviewable(file.mime_type) && (
                                <button
                                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                                  onClick={() => {
                                    setPreviewFile(file);
                                    setActionMenu(null);
                                  }}
                                >
                                  <Eye className="h-4 w-4" />
                                  Preview
                                </button>
                              )}
                              <button
                                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                                onClick={() => handleDownload(file.id)}
                              >
                                <Download className="h-4 w-4" />
                                Download
                              </button>
                              <button
                                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                                onClick={() => processMutation.mutate(file.id)}
                                disabled={processMutation.isPending}
                              >
                                <Play className="h-4 w-4" />
                                Process Document
                              </button>
                              <button
                                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-muted"
                                onClick={() => deleteMutation.mutate(file.id)}
                                disabled={deleteMutation.isPending}
                              >
                                <Trash2 className="h-4 w-4" />
                                Delete
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
          )}
        </CardContent>
      </Card>

      {showScan && <ScanModal onClose={() => setShowScan(false)} />}
      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}

      {previewFile && (
        <div
          className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          onClick={() => setPreviewFile(null)}
        >
          <div
            className="bg-background rounded-lg max-w-4xl max-h-[90vh] overflow-auto p-6 w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-medium">{previewFile.path.split("/").pop()}</h3>
              <Button variant="ghost" size="sm" onClick={() => setPreviewFile(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            {previewFile.mime_type.startsWith("image/") ? (
              <img
                src={`/api/v1/files/${previewFile.id}/download/`}
                alt={previewFile.path}
                className="max-w-full max-h-[70vh] object-contain mx-auto"
              />
            ) : previewFile.mime_type === "application/pdf" ? (
              <iframe
                src={`/api/v1/files/${previewFile.id}/download/`}
                className="w-full h-[70vh] border rounded"
                title={previewFile.path}
              />
            ) : (
              <pre className="text-sm whitespace-pre-wrap bg-muted p-4 rounded max-h-[70vh] overflow-auto">
                Preview not available for this file type
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
