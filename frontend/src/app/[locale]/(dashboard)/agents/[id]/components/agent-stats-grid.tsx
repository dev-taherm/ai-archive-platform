"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Globe, Cpu, HardDrive, Clock, ArrowRightLeft } from "lucide-react";
import { formatDate, formatBytes } from "@/lib/utils";
import type { Agent } from "@/types/api";

interface AgentStatsGridProps {
  agent: Agent;
  t: (key: string) => string;
}

export function AgentStatsGrid({ agent, t }: AgentStatsGridProps) {
  return (
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
  );
}
