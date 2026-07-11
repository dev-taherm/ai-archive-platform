"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import api from "@/lib/api";
import { formatDate, formatBytes } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { useToast } from "@/hooks/use-toast";
import type { Agent, AgentCommand } from "@/types/api";
import {
  ArrowLeft,
  Bot,
  Globe,
  Cpu,
  HardDrive,
  FolderOpen,
  Clock,
  RefreshCw,
  Send,
  Loader2,
  Trash2,
  Plus,
  Settings,
  AlertCircle,
  Pencil,
  Check,
  X,
  ArrowRightLeft,
  Copy,
} from "lucide-react";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning"> = {
  online: "success",
  syncing: "warning",
  offline: "secondary",
  error: "destructive",
};

const ALL_COMMAND_TYPES = [
  { value: "scan", label: "Scan" },
  { value: "sync", label: "Sync" },
  { value: "process", label: "Process" },
  { value: "restart", label: "Restart", destructive: true },
  { value: "shutdown", label: "Shutdown", destructive: true },
  { value: "config_update", label: "Config Update" },
  { value: "update", label: "Update Device" },
  { value: "start_scan", label: "Start Continuous Scan" },
  { value: "stop_scan", label: "Stop Continuous Scan" },
];

export default function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const t = useTranslations("agents");
  const tc = useTranslations("common");

  // Command state
  const [commandType, setCommandType] = useState("scan");
  const [showDestructiveConfirm, setShowDestructiveConfirm] = useState(false);

  // Delete agent
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Add folder state
  const [showAddFolder, setShowAddFolder] = useState(false);
  const [newFolderPath, setNewFolderPath] = useState("");
  const [newFolderLabel, setNewFolderLabel] = useState("");

  // Edit folder state
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  const [editingFolderPath, setEditingFolderPath] = useState("");
  const [editingFolderLabel, setEditingFolderLabel] = useState("");
  const [showDeleteFolder, setShowDeleteFolder] = useState<string | null>(null);

  // Edit agent settings state
  const [editingSettings, setEditingSettings] = useState(false);
  const [editName, setEditName] = useState("");
  const [editSyncInterval, setEditSyncInterval] = useState(0);
  const [editMaxFileSize, setEditMaxFileSize] = useState(0);

  // Queries
  const { data: agent, isLoading } = useQuery<Agent>({
    queryKey: ["agents", id],
    queryFn: async () => {
      const res = await api.get(`/agents/${id}`);
      return res.data;
    },
  });

  const { data: commands = [] } = useQuery<AgentCommand[]>({
    queryKey: ["agents", id, "commands"],
    queryFn: async () => {
      const res = await api.get(`/agents/${id}/commands`);
      return Array.isArray(res.data) ? res.data : res.data.commands || [];
    },
    enabled: !!agent,
  });

  // --- Mutations ---

  const sendCommand = useMutation({
    mutationFn: async (type: string) => {
      return api.post(`/agents/${id}/commands/create`, {
        command_type: type,
        payload: {},
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", id, "commands"] });
      toast({ title: t("commands"), description: t("commandQueued") });
    },
    onError: () => {
      toast({ title: t("failedToSendCommand"), variant: "destructive" });
    },
  });

  const deleteAgent = useMutation({
    mutationFn: async () => api.delete(`/agents/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      toast({ title: t("deleteDevice") });
      router.push("/agents");
    },
    onError: () => {
      toast({ title: t("failedToDeleteDevice"), variant: "destructive" });
    },
  });

  const addFolder = useMutation({
    mutationFn: async (data: { local_path: string; label: string }) => {
      return api.post(`/agents/${id}/folders`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", id] });
      toast({ title: "Folder added" });
      setShowAddFolder(false);
      setNewFolderPath("");
      setNewFolderLabel("");
    },
    onError: (err: any) => {
      toast({
        title: "Failed to add folder",
        description: err?.response?.data?.detail || "Unknown error",
        variant: "destructive",
      });
    },
  });

  const updateFolder = useMutation({
    mutationFn: async ({ folderId, data }: { folderId: string; data: Record<string, unknown> }) => {
      return api.patch(`/agents/${id}/folders/${folderId}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", id] });
      toast({ title: "Folder updated" });
      setEditingFolderId(null);
    },
    onError: (err: any) => {
      toast({
        title: "Failed to update folder",
        description: err?.response?.data?.detail || "Unknown error",
        variant: "destructive",
      });
    },
  });

  const deleteFolder = useMutation({
    mutationFn: async (folderId: string) => {
      return api.delete(`/agents/${id}/folders/${folderId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", id] });
      toast({ title: "Folder removed" });
      setShowDeleteFolder(null);
    },
    onError: () => {
      toast({ title: "Failed to remove folder", variant: "destructive" });
    },
  });

  const updateAgent = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      return api.patch(`/agents/${id}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", id] });
      toast({ title: "Device settings updated" });
      setEditingSettings(false);
    },
    onError: (err: any) => {
      toast({
        title: "Failed to update device",
        description: err?.response?.data?.detail || "Unknown error",
        variant: "destructive",
      });
    },
  });

  // --- Handlers ---

  const handleSendCommand = () => {
    const cmd = ALL_COMMAND_TYPES.find((c) => c.value === commandType);
    if (cmd?.destructive) {
      setShowDestructiveConfirm(true);
    } else {
      sendCommand.mutate(commandType);
    }
  };

  const handleConfirmDestructive = () => {
    setShowDestructiveConfirm(false);
    sendCommand.mutate(commandType);
  };

  const startEditSettings = () => {
    if (!agent) return;
    setEditName(agent.name);
    setEditSyncInterval(agent.sync_interval_minutes);
    setEditMaxFileSize(agent.max_file_size_mb);
    setEditingSettings(true);
  };

  const handleSaveSettings = () => {
    updateAgent.mutate({
      name: editName,
      sync_interval_minutes: editSyncInterval,
      max_file_size_mb: editMaxFileSize,
    });
  };

  const startEditFolder = (folder: { id: string; local_path: string; label: string }) => {
    setEditingFolderId(folder.id);
    setEditingFolderPath(folder.local_path);
    setEditingFolderLabel(folder.label);
  };

  const handleSaveFolder = (folderId: string) => {
    updateFolder.mutate({
      folderId,
      data: { local_path: editingFolderPath, label: editingFolderLabel },
    });
  };

  // --- Loading / Empty states ---

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6 animate-pulse">
                <div className="h-4 w-32 rounded bg-muted mb-2" />
                <div className="h-8 w-24 rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <AlertCircle className="h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">{t('notFound')}</p>
        <Button variant="outline" onClick={() => router.push("/agents")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          {t('backToDevices')}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/agents")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-muted p-2">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{agent.name}</h1>
              <p className="text-sm text-muted-foreground">{agent.agent_id}</p>
            </div>
          </div>
          <Badge variant={statusVariant[agent.status] || "secondary"}>
            {agent.status}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["agents", id] })}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            {tc('refresh')}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {tc('delete')}
          </Button>
        </div>
      </div>

      {/* Stats Grid - includes last_sync_at */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-brand-teal/10 p-2">
                <Globe className="h-4 w-4 text-brand-teal" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('platform')}</p>
                <p className="text-sm font-medium">
                  {agent.platform} &middot; {agent.hostname}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-brand-cyan/10 p-2">
                <Cpu className="h-4 w-4 text-brand-cyan" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('version')}</p>
                <p className="text-sm font-medium">v{agent.agent_version}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-brand-teal/10 p-2">
                <HardDrive className="h-4 w-4 text-brand-teal" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('files')}</p>
                <p className="text-sm font-medium">{agent.files_count}</p>
                <p className="text-xs text-muted-foreground">
                  {formatBytes(agent.total_size_bytes)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-brand-cyan/10 p-2">
                <Clock className="h-4 w-4 text-brand-cyan" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('lastSeen')}</p>
                <p className="text-sm font-medium">
                  {agent.last_seen ? formatDate(agent.last_seen) : t('neverSeen')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-brand-teal/10 p-2">
                <ArrowRightLeft className="h-4 w-4 text-brand-teal" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('lastSync')}</p>
                <p className="text-sm font-medium">
                  {agent.last_sync_at ? formatDate(agent.last_sync_at) : t('neverSeen')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Commands Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Send className="h-4 w-4" />
              {t('commands')}
            </CardTitle>
            <div className="flex items-center gap-2">
              <select
                value={commandType}
                onChange={(e) => setCommandType(e.target.value)}
                className="rounded-md border bg-background px-3 py-1.5 text-sm"
              >
                {ALL_COMMAND_TYPES.map((cmd) => (
                  <option key={cmd.value} value={cmd.value}>
                    {cmd.label}{cmd.destructive ? " ⚠️" : ""}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                onClick={handleSendCommand}
                disabled={sendCommand.isPending}
              >
                {sendCommand.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1 text-brand-teal" />
                ) : (
                  <Send className="h-4 w-4 mr-1" />
                )}
                {t('send')}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {commands.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              {t('noCommands')}
            </p>
          ) : (
            <div className="space-y-2">
              {commands.map((cmd) => (
                <div
                  key={cmd.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={
                      cmd.status === "completed" ? "success" :
                      cmd.status === "failed" ? "destructive" : "secondary"
                    }>
                      {cmd.status}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium">{cmd.command_type}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(cmd.created_at)}
                      </p>
                    </div>
                  </div>
                  {cmd.result && (
                    <p className="text-xs text-muted-foreground max-w-xs truncate">
                      {typeof cmd.result === "string" ? cmd.result : JSON.stringify(cmd.result)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Folders Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              {t('monitoredFolders', { count: agent.folders?.length || 0 })}
            </CardTitle>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAddFolder(!showAddFolder)}
            >
              <Plus className="h-4 w-4 mr-1" />
              {t('addFolder')}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {showAddFolder && (
            <div className="mb-4 p-4 rounded-lg border bg-muted/50 space-y-2">
              <Input
                placeholder={t('folderPathPlaceholder')}
                value={newFolderPath}
                onChange={(e) => setNewFolderPath(e.target.value)}
              />
              <Input
                placeholder={t('folderLabelPlaceholder')}
                value={newFolderLabel}
                onChange={(e) => setNewFolderLabel(e.target.value)}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => addFolder.mutate({ local_path: newFolderPath, label: newFolderLabel })}
                  disabled={!newFolderPath.trim() || addFolder.isPending}
                >
                  {addFolder.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1 text-brand-teal" />
                  ) : (
                    <Plus className="h-4 w-4 mr-1" />
                  )}
                  {t('addFolder')}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowAddFolder(false)}>
                  {tc('cancel')}
                </Button>
              </div>
            </div>
          )}
          {!agent.folders || agent.folders.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              {t('noFolders')}
            </p>
          ) : (
            <div className="space-y-2">
              {agent.folders.map((folder) => (
                <div
                  key={folder.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  {editingFolderId === folder.id ? (
                    /* Inline edit mode */
                    <div className="flex-1 flex items-center gap-2">
                      <Input
                        value={editingFolderPath}
                        onChange={(e) => setEditingFolderPath(e.target.value)}
                        className="flex-1"
                        placeholder={t('folderPathPlaceholder')}
                      />
                      <Input
                        value={editingFolderLabel}
                        onChange={(e) => setEditingFolderLabel(e.target.value)}
                        className="w-40"
                        placeholder={t('folderLabelPlaceholder')}
                      />
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleSaveFolder(folder.id)}
                        disabled={updateFolder.isPending}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditingFolderId(null)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    /* Display mode */
                    <>
                      <div className="flex items-center gap-3">
                        <FolderOpen className="h-4 w-4 text-brand-teal" />
                        <div>
                          <p className="text-sm font-medium">{folder.local_path}</p>
                          {folder.label && (
                            <p className="text-xs text-muted-foreground">{folder.label}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{t('countFiles', { count: folder.file_count })}</span>
                        <Badge variant={folder.is_active ? "success" : "secondary"}>
                          {folder.is_active ? t('active') : t('inactive')}
                        </Badge>
                        {folder.last_scanned_at && (
                          <span>{t('scanned', { date: formatDate(folder.last_scanned_at) })}</span>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => startEditFolder(folder)}
                          title={tc('edit')}
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setShowDeleteFolder(folder.id)}
                          title={t('removeFolder')}
                        >
                          <Trash2 className="h-3 w-3 text-destructive" />
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Agent Configuration / Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Settings className="h-4 w-4" />
              {t('deviceConfiguration')}
            </CardTitle>
            {!editingSettings && (
              <Button size="sm" variant="outline" onClick={startEditSettings}>
                <Pencil className="h-4 w-4 mr-1" />
                {tc('edit')}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {editingSettings ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">{t('deviceName')}</p>
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">{t('syncInterval')}</p>
                  <Input
                    type="number"
                    value={editSyncInterval}
                    onChange={(e) => setEditSyncInterval(Number(e.target.value))}
                    min={1}
                  />
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">{t('maxFileSize')}</p>
                  <Input
                    type="number"
                    value={editMaxFileSize}
                    onChange={(e) => setEditMaxFileSize(Number(e.target.value))}
                    min={1}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleSaveSettings}
                  disabled={updateAgent.isPending}
                >
                  {updateAgent.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1 text-brand-teal" />
                  ) : (
                    <Check className="h-4 w-4 mr-1" />
                  )}
                  {tc('save')}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setEditingSettings(false)}>
                  {tc('cancel')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{t('syncInterval')}</p>
                <p className="text-sm">{t('syncIntervalValue', { n: agent.sync_interval_minutes })}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{t('maxFileSize')}</p>
                <p className="text-sm">{t('maxFileSizeValue', { n: agent.max_file_size_mb })}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{t('pendingCommands')}</p>
                <p className="text-sm">{agent.pending_commands_count}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{t('ipAddress')}</p>
                <p className="text-sm">{agent.ip_address || "N/A"}</p>
              </div>
            </div>
          )}
          {agent.capabilities && agent.capabilities.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-muted-foreground mb-2">{t('capabilities')}</p>
              <div className="flex flex-wrap gap-1">
                {agent.capabilities.map((cap) => (
                  <Badge key={cap} variant="outline" className="text-xs">
                    {cap}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Agent Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('deleteDevice')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('deleteDeviceConfirm')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteAgent.mutate()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {tc('delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Destructive Command Confirm */}
      <AlertDialog open={showDestructiveConfirm} onOpenChange={setShowDestructiveConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('confirmCommand', { commandType })}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('confirmCommandDesc', { commandType })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDestructive}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('sendCommand')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Folder Confirm */}
      <AlertDialog open={!!showDeleteFolder} onOpenChange={() => setShowDeleteFolder(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('removeFolder')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('removeFolderConfirm')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => showDeleteFolder && deleteFolder.mutate(showDeleteFolder)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('remove')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
