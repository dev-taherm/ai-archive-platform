"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { FileRecord, Agent } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Search,
  FolderOpen,
  MoreVertical,
  Trash2,
  Play,
  FileIcon,
  FileImage,
  FileSpreadsheet,
  FileCode,
  RefreshCw,
  Loader2,
  Bot,
  ArrowRightLeft,
} from "lucide-react";
import Link from "next/link";
import { formatBytes, formatDateTime } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { useTranslations } from "next-intl";

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
  const t = useTranslations("files");
  const tc = useTranslations("common");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [actionMenu, setActionMenu] = useState<string | null>(null);

  // Move file state
  const [showMoveDialog, setShowMoveDialog] = useState<string | null>(null); // file ID
  const [moveTargetAgent, setMoveTargetAgent] = useState("");
  const [moveSourcePath, setMoveSourcePath] = useState("");
  const [moveTargetPath, setMoveTargetPath] = useState("");
  const [moveMode, setMoveMode] = useState<"agent" | "folder">("agent");

  // Files query
  const { data: files = [], isLoading } = useQuery<FileRecord[]>({
    queryKey: ["files"],
    queryFn: async () => {
      const res = await api.get("/files");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
  });

  // Agents query (for move dialog)
  const { data: agents = [] } = useQuery<Agent[]>({
    queryKey: ["agents"],
    queryFn: async () => {
      const res = await api.get("/agents");
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
      const res = await api.post("/documents/process-pipeline", { file_id: fileId }, { timeout: 120000 });
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setActionMenu(null);
      if (data.error) {
        toast({ title: "Processing failed", description: data.error, variant: "destructive" });
      } else {
        toast({
          title: "Document processed",
          description: `Classification: ${data.classification || "N/A"}, Chunks: ${data.chunk_count ?? 0}`,
        });
      }
    },
    onError: (error: any) => {
      toast({
        title: "Processing failed",
        description: error?.response?.data?.detail || error?.message || "Server error",
        variant: "destructive",
      });
    },
  });

  const moveFileAgent = useMutation({
    mutationFn: async ({ fileId, targetAgentId, sourceAgentId }: { fileId: string; targetAgentId: string; sourceAgentId: string }) => {
      return api.post(`/agents/${sourceAgentId}/files/move`, {
        file_ids: [fileId],
        target_agent_id: targetAgentId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      toast({ title: "File moved to target device" });
      setShowMoveDialog(null);
      setMoveTargetAgent("");
    },
    onError: (err: any) => {
      toast({
        title: "Failed to move file",
        description: err?.response?.data?.detail || "Unknown error",
        variant: "destructive",
      });
    },
  });

  const moveFileFolder = useMutation({
    mutationFn: async ({ fileId, agentId, sourcePath, targetPath }: { fileId: string; agentId: string; sourcePath: string; targetPath: string }) => {
      return api.post(`/agents/${agentId}/files/move-folder`, {
        file_ids: [fileId],
        source_path: sourcePath,
        target_path: targetPath,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      toast({ title: "File moved within device" });
      setShowMoveDialog(null);
      setMoveSourcePath("");
      setMoveTargetPath("");
    },
    onError: (err: any) => {
      toast({
        title: "Failed to move file",
        description: err?.response?.data?.detail || "Unknown error",
        variant: "destructive",
      });
    },
  });

  const handleMoveFile = (fileId: string) => {
    const file = files.find((f) => f.id === fileId);
    if (!file) return;

    if (moveMode === "agent") {
      if (!moveTargetAgent) {
        toast({ title: t("selectTargetDevice"), variant: "destructive" });
        return;
      }
      // Find the source agent from agents list
      const sourceAgent = agents.find((a) =>
        a.folders?.some((f) => file.path.startsWith(f.local_path))
      );
      if (!sourceAgent) {
        toast({ title: t("cannotDetermineSource"), variant: "destructive" });
        return;
      }
      moveFileAgent.mutate({
        fileId,
        targetAgentId: moveTargetAgent,
        sourceAgentId: sourceAgent.agent_id,
      });
    } else {
      if (!moveSourcePath || !moveTargetPath) {
        toast({ title: t("enterSourceTargetPaths"), variant: "destructive" });
        return;
      }
      const sourceAgent = agents.find((a) =>
        a.folders?.some((f) => file.path.startsWith(f.local_path))
      );
      if (!sourceAgent) {
        toast({ title: t("cannotDetermineSource"), variant: "destructive" });
        return;
      }
      moveFileFolder.mutate({
        fileId,
        agentId: sourceAgent.agent_id,
        sourcePath: moveSourcePath,
        targetPath: moveTargetPath,
      });
    }
  };

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
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
          <p className="text-muted-foreground">
            {t("subtitle")}
          </p>
        </div>
      </div>

      {files.length === 0 && !isLoading ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Bot className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
            <p className="text-lg font-medium">{t("emptyHeading")}</p>
            <p className="mb-4 mt-1 max-w-sm text-sm text-muted-foreground">
              {t("emptyDescription")}
            </p>
            <Link href="/agents">
              <Button>
                <Bot className="mr-2 h-4 w-4" />
                {t("setUpDevice")}
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t("searchPlaceholder")}
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
                {t("loading")}
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <FolderOpen className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
                <p className="text-lg font-medium">{t("noSearchResults")}</p>
                <p className="text-sm">{t("noSearchResultsDesc")}</p>
              </div>
            ) : (
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
                                <button
                                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                                  onClick={() => processMutation.mutate(file.id)}
                                  disabled={processMutation.isPending}
                                >
                                  {processMutation.isPending ? (
                                    <Loader2 className="h-4 w-4 animate-spin text-brand-teal" />
                                  ) : (
                                    <Play className="h-4 w-4" />
                                  )}
                                  {processMutation.isPending ? t("processing") : t("processDocument")}
                                </button>
                                <button
                                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                                  onClick={() => {
                                    setActionMenu(null);
                                    setShowMoveDialog(file.id);
                                    setMoveMode("agent");
                                    setMoveTargetAgent("");
                                    setMoveSourcePath("");
                                    setMoveTargetPath("");
                                  }}
                                >
                                  <ArrowRightLeft className="h-4 w-4" />
                                  {t("moveFile")}
                                </button>
                                <button
                                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-muted"
                                  onClick={() => deleteMutation.mutate(file.id)}
                                  disabled={deleteMutation.isPending}
                                >
                                  <Trash2 className="h-4 w-4" />
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
            )}
          </CardContent>
        </Card>
      )}

      {/* Move File Dialog */}
      <AlertDialog open={!!showMoveDialog} onOpenChange={() => setShowMoveDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("moveFileTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("moveFileDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex gap-2">
              <Button
                size="sm"
                variant={moveMode === "agent" ? "default" : "outline"}
                onClick={() => setMoveMode("agent")}
              >
                {t("moveToDevice")}
              </Button>
              <Button
                size="sm"
                variant={moveMode === "folder" ? "default" : "outline"}
                onClick={() => setMoveMode("folder")}
              >
                {t("moveToFolder")}
              </Button>
            </div>

            {moveMode === "agent" ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">{t("targetDevice")}</p>
                <select
                  value={moveTargetAgent}
                  onChange={(e) => setMoveTargetAgent(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                >
                  <option value="">{t("selectDevice")}</option>
                  {agents.map((a) => (
                    <option key={a.agent_id} value={a.agent_id}>
                      {a.name} ({a.agent_id})
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="space-y-2">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">{t("sourcePathPrefix")}</p>
                  <Input
                    placeholder={t("sourcePathPlaceholder")}
                    value={moveSourcePath}
                    onChange={(e) => setMoveSourcePath(e.target.value)}
                  />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">{t("targetPathPrefix")}</p>
                  <Input
                    placeholder={t("targetPathPlaceholder")}
                    value={moveTargetPath}
                    onChange={(e) => setMoveTargetPath(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => showMoveDialog && handleMoveFile(showMoveDialog)}
            >
                {(moveFileAgent.isPending || moveFileFolder.isPending) && (
                <Loader2 className="h-4 w-4 animate-spin mr-1 text-brand-teal" />
              )}
              {t("moveFile")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
