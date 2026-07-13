"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Settings, Pencil, Check, Loader2 } from "lucide-react";
import type { Agent } from "@/types/api";

interface AgentSettingsCardProps {
  agent: Agent;
  editing: boolean;
  editName: string;
  editSyncInterval: number;
  editMaxFileSize: number;
  editSyncScope: "personal" | "organization";
  onEditNameChange: (v: string) => void;
  onEditSyncIntervalChange: (v: number) => void;
  onEditMaxFileSizeChange: (v: number) => void;
  onEditSyncScopeChange: (v: "personal" | "organization") => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSave: () => void;
  saving: boolean;
  t: (key: string, params?: Record<string, any>) => string;
  tCommon: (key: string) => string;
}

export function AgentSettingsCard({
  agent,
  editing,
  editName,
  editSyncInterval,
  editMaxFileSize,
  editSyncScope,
  onEditNameChange,
  onEditSyncIntervalChange,
  onEditMaxFileSizeChange,
  onEditSyncScopeChange,
  onStartEdit,
  onCancelEdit,
  onSave,
  saving,
  t,
  tCommon,
}: AgentSettingsCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-4 w-4" />
            {t('deviceConfiguration')}
          </CardTitle>
          {!editing && (
            <Button size="sm" variant="outline" onClick={onStartEdit}>
              <Pencil className="h-4 w-4 mr-1" />
              {tCommon('edit')}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {editing ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{t('deviceName')}</p>
                <Input
                  value={editName}
                  onChange={(e) => onEditNameChange(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{t('syncInterval')}</p>
                <Input
                  type="number"
                  value={editSyncInterval}
                  onChange={(e) => onEditSyncIntervalChange(Number(e.target.value))}
                  min={1}
                />
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{t('maxFileSize')}</p>
                <Input
                  type="number"
                  value={editMaxFileSize}
                  onChange={(e) => onEditMaxFileSizeChange(Number(e.target.value))}
                  min={1}
                />
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t('syncScope')}</p>
              <select
                value={editSyncScope}
                onChange={(e) => onEditSyncScopeChange(e.target.value as "personal" | "organization")}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="personal">{tCommon('scopePersonal')}</option>
                <option value="organization">{tCommon('scopeOrganization')}</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={onSave}
                disabled={saving}
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1 text-brand-teal" />
                ) : (
                  <Check className="h-4 w-4 mr-1" />
                )}
                {tCommon('save')}
              </Button>
              <Button size="sm" variant="outline" onClick={onCancelEdit}>
                {tCommon('cancel')}
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
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t('syncScope')}</p>
              <p className="text-sm">{agent.sync_scope === 'organization' ? tCommon('scopeOrganization') : tCommon('scopePersonal')}</p>
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
  );
}
