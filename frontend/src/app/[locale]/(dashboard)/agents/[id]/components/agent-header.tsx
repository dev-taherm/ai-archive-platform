"use client";

import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Bot, RefreshCw, Trash2 } from "lucide-react";
import { agentStatusVariant as statusVariant } from "@/lib/constants";
import type { Agent } from "@/types/api";
import type { FunctionComponent } from "react";

interface AgentHeaderProps {
  agent: Agent;
  onRefresh: () => void;
  onDelete: () => void;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}

export function AgentHeader({ agent, onRefresh, onDelete, t, tCommon }: AgentHeaderProps) {
  const router = useRouter();

  return (
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
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          {tCommon('refresh')}
        </Button>
        <Button variant="destructive" size="sm" onClick={onDelete}>
          <Trash2 className="h-4 w-4 mr-2" />
          {tCommon('delete')}
        </Button>
      </div>
    </div>
  );
}
