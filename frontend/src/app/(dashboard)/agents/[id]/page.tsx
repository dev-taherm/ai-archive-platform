"use client";

import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { formatDate, formatBytes } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
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
import type { Agent } from "@/types/api";
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
  Play,
  Square,
  Settings,
  Activity,
  FileText,
  AlertCircle,
} from "lucide-react";
import { useState } from "react";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning"> = {
  online: "success",
  syncing: "warning",
  offline: "secondary",
  error: "destructive",
};

interface Command {
  id: string;
  command_type: string;
  payload: Record<string, unknown>;
  status: string;
  result: string | null;
  created_at: string;
  executed_at: string | null;
}

export default function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [commandType, setCommandType] = useState("scan");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showAddFolder, setShowAddFolder] = useState(false);
  const [newFolderPath, setNewFolderPath] = useState("");
  const [newFolderLabel, setNewFolderLabel] = useState("");

  const { data: agent, isLoading } = useQuery<Agent>({
    queryKey: ["agents", id],
    queryFn: async () => {
      const res = await api.get(`/agents/${id}`);
      return res.data;
    },
  });

  const { data: commands = [] } = useQuery<Command[]>({
    queryKey: ["agents", id, "commands"],
    queryFn: async () => {
      const res = await api.get(`/agents/${id}/commands`);
      return Array.isArray(res.data) ? res.data : res.data.commands || [];
    },
    enabled: !!agent,
  });

  const sendCommand = useMutation({
    mutationFn: async (type: string) => {
      return api.post(`/agents/${id}/commands/create`, {
        command_type: type,
        payload: {},
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", id, "commands"] });
      toast({ title: "Command sent", description: "Command has been queued for the agent." });
    },
    onError: () => {
      toast({ title: "Failed to send command", variant: "destructive" });
    },
  });

  const deleteAgent = useMutation({
    mutationFn: async () => {
      return api.delete(`/agents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      toast({ title: "Agent deleted" });
      router.push("/agents");
    },
    onError: () => {
      toast({ title: "Failed to delete agent", variant: "destructive" });
    },
  });

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
        <p className="text-lg font-medium">Agent not found</p>
        <Button variant="outline" onClick={() => router.push("/agents")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Agents
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
              <h1 className="text-2xl font-bold">{agent.name}</h1>
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
            Refresh
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-muted p-2">
                <Globe className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Platform</p>
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
              <div className="rounded-md bg-muted p-2">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Version</p>
                <p className="text-sm font-medium">v{agent.agent_version}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-muted p-2">
                <HardDrive className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Files</p>
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
              <div className="rounded-md bg-muted p-2">
                <Clock className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Last Seen</p>
                <p className="text-sm font-medium">
                  {agent.last_seen ? formatDate(agent.last_seen) : "Never"}
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
              Commands
            </CardTitle>
            <div className="flex items-center gap-2">
              <select
                value={commandType}
                onChange={(e) => setCommandType(e.target.value)}
                className="rounded-md border bg-background px-3 py-1.5 text-sm"
              >
                <option value="scan">Scan</option>
                <option value="sync">Sync</option>
                <option value="process">Process</option>
                <option value="restart">Restart</option>
                <option value="config_update">Config Update</option>
              </select>
              <Button
                size="sm"
                onClick={() => sendCommand.mutate(commandType)}
                disabled={sendCommand.isPending}
              >
                {sendCommand.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <Send className="h-4 w-4 mr-1" />
                )}
                Send
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {commands.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No commands sent yet
            </p>
          ) : (
            <div className="space-y-2">
              {commands.map((cmd) => (
                <div
                  key={cmd.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={cmd.status === "completed" ? "success" : cmd.status === "failed" ? "destructive" : "secondary"}>
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
                      {cmd.result}
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
              Monitored Folders ({agent.folders?.length || 0})
            </CardTitle>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAddFolder(!showAddFolder)}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Folder
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {showAddFolder && (
            <div className="mb-4 p-4 rounded-lg border bg-muted/50 space-y-2">
              <Input
                placeholder="/path/to/folder"
                value={newFolderPath}
                onChange={(e) => setNewFolderPath(e.target.value)}
              />
              <Input
                placeholder="Label (optional)"
                value={newFolderLabel}
                onChange={(e) => setNewFolderLabel(e.target.value)}
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={() => {
                  setShowAddFolder(false);
                  setNewFolderPath("");
                  setNewFolderLabel("");
                }}>
                  Add
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowAddFolder(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
          {!agent.folders || agent.folders.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No folders configured
            </p>
          ) : (
            <div className="space-y-2">
              {agent.folders.map((folder) => (
                <div
                  key={folder.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <FolderOpen className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{folder.local_path}</p>
                      {folder.label && (
                        <p className="text-xs text-muted-foreground">{folder.label}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{folder.file_count} files</span>
                    <Badge variant={folder.is_active ? "success" : "secondary"}>
                      {folder.is_active ? "Active" : "Inactive"}
                    </Badge>
                    {folder.last_scanned_at && (
                      <span>Scanned: {formatDate(folder.last_scanned_at)}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Agent Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Agent Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Sync Interval</p>
              <p className="text-sm">{agent.sync_interval_minutes} minutes</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Max File Size</p>
              <p className="text-sm">{agent.max_file_size_mb} MB</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Pending Commands</p>
              <p className="text-sm">{agent.pending_commands_count}</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">IP Address</p>
              <p className="text-sm">{agent.ip_address || "N/A"}</p>
            </div>
          </div>
          {agent.capabilities && agent.capabilities.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-muted-foreground mb-2">Capabilities</p>
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

      {/* Delete Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Agent</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this agent? This action cannot be undone.
              The agent will be disconnected and all its data will be removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteAgent.mutate()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
