"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import api from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import type { Agent, AgentCommand } from "@/types/api";
import { ArrowLeft, AlertCircle } from "lucide-react";

import { AgentHeader } from "./components/agent-header";
import { AgentStatsGrid } from "./components/agent-stats-grid";
import { AgentCommandsSection, ALL_COMMAND_TYPES } from "./components/agent-commands-section";
import { AgentFoldersSection } from "./components/agent-folders-section";
import { AgentSettingsCard } from "./components/agent-settings-card";
import { DeleteConfirmDialogs } from "./components/delete-confirm-dialogs";

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
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
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

  const handleSendCommand = (type: string) => {
    const cmd = ALL_COMMAND_TYPES.find((c) => c.value === type);
    if (cmd?.destructive) {
      setShowDestructiveConfirm(true);
    } else {
      sendCommand.mutate(type);
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

  const handleDeleteFolderConfirm = () => {
    if (showDeleteFolder) {
      deleteFolder.mutate(showDeleteFolder);
    }
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
      <AgentHeader
        agent={agent}
        onRefresh={() => queryClient.invalidateQueries({ queryKey: ["agents", id] })}
        onDelete={() => setShowDeleteDialog(true)}
        t={t}
        tCommon={tc}
      />

      <AgentStatsGrid agent={agent} t={t} />

      <AgentCommandsSection
        commands={commands}
        onSendCommand={handleSendCommand}
        commandType={commandType}
        onCommandTypeChange={setCommandType}
        sending={sendCommand.isPending}
        t={t}
      />

      <AgentFoldersSection
        agentId={id}
        folders={agent.folders || []}
        onAddFolder={(path, label) => addFolder.mutate({ local_path: path, label })}
        onUpdateFolder={(folderId, path, label) =>
          updateFolder.mutate({ folderId, data: { local_path: path, label } })
        }
        onDeleteFolder={(folderId) => setShowDeleteFolder(folderId)}
        addingFolder={addFolder.isPending}
        t={t}
        tCommon={tc}
      />

      <AgentSettingsCard
        agent={agent}
        editing={editingSettings}
        editName={editName}
        editSyncInterval={editSyncInterval}
        editMaxFileSize={editMaxFileSize}
        onEditNameChange={setEditName}
        onEditSyncIntervalChange={setEditSyncInterval}
        onEditMaxFileSizeChange={setEditMaxFileSize}
        onStartEdit={startEditSettings}
        onCancelEdit={() => setEditingSettings(false)}
        onSave={handleSaveSettings}
        saving={updateAgent.isPending}
        t={t}
        tCommon={tc}
      />

      <DeleteConfirmDialogs
        showDeleteDialog={showDeleteDialog}
        onDeleteChange={setShowDeleteDialog}
        showDestructiveConfirm={showDestructiveConfirm}
        onDestructiveChange={setShowDestructiveConfirm}
        showDeleteFolder={showDeleteFolder}
        onDeleteFolderChange={setShowDeleteFolder}
        onDeleteAgent={() => deleteAgent.mutate()}
        onConfirmDestructive={handleConfirmDestructive}
        onDeleteFolderConfirm={handleDeleteFolderConfirm}
        commandType={commandType}
        t={t}
        tCommon={tc}
      />
    </div>
  );
}
