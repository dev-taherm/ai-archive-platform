"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Send, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { AgentCommand } from "@/types/api";

export const ALL_COMMAND_TYPES = [
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

interface AgentCommandsSectionProps {
  commands: AgentCommand[];
  onSendCommand: (type: string) => void;
  commandType: string;
  onCommandTypeChange: (type: string) => void;
  sending: boolean;
  t: (key: string) => string;
}

export function AgentCommandsSection({
  commands,
  onSendCommand,
  commandType,
  onCommandTypeChange,
  sending,
  t,
}: AgentCommandsSectionProps) {
  return (
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
              onChange={(e) => onCommandTypeChange(e.target.value)}
              className="rounded-md border bg-background px-3 py-1.5 text-sm"
            >
              {ALL_COMMAND_TYPES.map((cmd) => (
                <option key={cmd.value} value={cmd.value}>
                  {cmd.label}{cmd.destructive ? " \u26A0\uFE0F" : ""}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              onClick={() => onSendCommand(commandType)}
              disabled={sending}
            >
              {sending ? (
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
  );
}
