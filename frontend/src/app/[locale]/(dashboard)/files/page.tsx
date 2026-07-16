"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { FileRecord, Agent } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Search, FolderOpen, RefreshCw, Bot } from "lucide-react";
import Link from "next/link";
import { useToast } from "@/hooks/use-toast";
import { useTranslations } from "next-intl";
import FilesTable from "./components/files-table";
import MoveFileDialog from "./components/move-file-dialog";
import ScopeSelector from "@/components/features/shared/scope-selector";

export default function FilesPage() {
  const t = useTranslations("files");
  const tc = useTranslations("common");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [actionMenu, setActionMenu] = useState<string | null>(null);
  const [showMoveDialog, setShowMoveDialog] = useState<string | null>(null);
  const [moveTargetAgent, setMoveTargetAgent] = useState("");
  const [moveSourcePath, setMoveSourcePath] = useState("");
  const [moveTargetPath, setMoveTargetPath] = useState("");
  const [moveMode, setMoveMode] = useState<"agent" | "folder">("agent");
  const [scope, setScope] = useState<"personal" | "organization">("personal");

  const { data: files = [], isLoading } = useQuery<FileRecord[]>({
    queryKey: ["files", scope],
    queryFn: async () => {
      const res = await api.get("/files", { params: { scope } });
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
  });

  const { data: agents = [] } = useQuery<Agent[]>({
    queryKey: ["agents"],
    queryFn: async () => {
      const res = await api.get("/agents");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => { await api.delete(`/files/${id}`); },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["files"] }); setActionMenu(null); },
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
        toast({ title: "Document processed", description: `Classification: ${data.classification || "N/A"}, Chunks: ${data.chunk_count ?? 0}` });
      }
    },
    onError: (error: any) => {
      toast({ title: "Processing failed", description: error?.response?.data?.detail || error?.message || "Server error", variant: "destructive" });
    },
  });

  const moveFileAgent = useMutation({
    mutationFn: async ({ fileId, targetAgentId, sourceAgentId }: { fileId: string; targetAgentId: string; sourceAgentId: string }) => {
      return api.post(`/agents/${sourceAgentId}/files/move`, { file_ids: [fileId], target_agent_id: targetAgentId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      toast({ title: "File moved to target device" });
      setShowMoveDialog(null);
      setMoveTargetAgent("");
    },
    onError: (err: any) => {
      toast({ title: "Failed to move file", description: err?.response?.data?.detail || "Unknown error", variant: "destructive" });
    },
  });

  const moveFileFolder = useMutation({
    mutationFn: async ({ fileId, agentId, sourcePath, targetPath }: { fileId: string; agentId: string; sourcePath: string; targetPath: string }) => {
      return api.post(`/agents/${agentId}/files/move-folder`, { file_ids: [fileId], source_path: sourcePath, target_path: targetPath });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      toast({ title: "File moved within device" });
      setShowMoveDialog(null);
      setMoveSourcePath("");
      setMoveTargetPath("");
    },
    onError: (err: any) => {
      toast({ title: "Failed to move file", description: err?.response?.data?.detail || "Unknown error", variant: "destructive" });
    },
  });

  const handleMoveFile = (fileId: string) => {
    const file = files.find((f) => f.id === fileId);
    if (!file) return;
    const findSource = () => agents.find((a) => a.folders?.some((f) => file.path.startsWith(f.local_path)));
    if (moveMode === "agent") {
      if (!moveTargetAgent) { toast({ title: t("selectTargetDevice"), variant: "destructive" }); return; }
      const src = findSource();
      if (!src) { toast({ title: t("cannotDetermineSource"), variant: "destructive" }); return; }
      moveFileAgent.mutate({ fileId, targetAgentId: moveTargetAgent, sourceAgentId: src.agent_id });
    } else {
      if (!moveSourcePath || !moveTargetPath) { toast({ title: t("enterSourceTargetPaths"), variant: "destructive" }); return; }
      const src = findSource();
      if (!src) { toast({ title: t("cannotDetermineSource"), variant: "destructive" }); return; }
      moveFileFolder.mutate({ fileId, agentId: src.agent_id, sourcePath: moveSourcePath, targetPath: moveTargetPath });
    }
  };
  const filtered = files.filter((f) => f.path.toLowerCase().includes(search.toLowerCase()) || f.mime_type.toLowerCase().includes(search.toLowerCase()) || f.tags.some((tg) => tg.toLowerCase().includes(search.toLowerCase())));
  const handleAction = (action: string, file: FileRecord) => {
    setActionMenu(null);
    if (action === "process") processMutation.mutate(file.id);
    else if (action === "move") { setShowMoveDialog(file.id); setMoveMode("agent"); setMoveTargetAgent(""); setMoveSourcePath(""); setMoveTargetPath(""); }
    else if (action === "delete") deleteMutation.mutate(file.id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <ScopeSelector value={scope} onChange={setScope} />
      </div>

      {files.length === 0 && !isLoading ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Bot className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
            <p className="text-lg font-medium">{t("emptyHeading")}</p>
            <p className="mb-4 mt-1 max-w-sm text-sm text-muted-foreground">{t("emptyDescription")}</p>
            <Link href="/agents">
              <Button><Bot className="mr-2 h-4 w-4" />{t("setUpDevice")}</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Input placeholder={t("searchPlaceholder")} value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-sm" />
              <Button variant="ghost" size="icon" onClick={() => queryClient.invalidateQueries({ queryKey: ["files"] })}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8 text-muted-foreground">{t("loading")}</div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <FolderOpen className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
                <p className="text-lg font-medium">{t("noSearchResults")}</p>
                <p className="text-sm">{t("noSearchResultsDesc")}</p>
              </div>
            ) : (
              <FilesTable
                files={filtered} onAction={handleAction}
                processingId={processMutation.isPending ? "pending" : null}
                actionMenu={actionMenu} onToggleMenu={(id) => setActionMenu(actionMenu === id ? null : id)}
                t={t} tc={tc}
              />
            )}
          </CardContent>
        </Card>
      )}

      <MoveFileDialog
        open={!!showMoveDialog}
        onOpenChange={() => setShowMoveDialog(null)}
        file={showMoveDialog ? files.find((f) => f.id === showMoveDialog) || null : null}
        agents={agents}
        moveMode={moveMode} moveTargetAgent={moveTargetAgent}
        moveSourcePath={moveSourcePath} moveTargetPath={moveTargetPath}
        onMoveModeChange={setMoveMode} onMoveTargetAgentChange={setMoveTargetAgent}
        onMoveSourcePathChange={setMoveSourcePath} onMoveTargetPathChange={setMoveTargetPath}
        onConfirm={() => showMoveDialog && handleMoveFile(showMoveDialog)}
        isMoving={moveFileAgent.isPending || moveFileFolder.isPending}
        t={t} tc={tc}
      />
    </div>
  );
}
