"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  Bot,
  Cpu,
  Globe,
  HardDrive,
  Clock,
  FolderOpen,
  Plus,
  Download,
} from "lucide-react";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DownloadAgentDialog } from "@/components/features/agents/download-agent-dialog";
import type { Agent } from "@/types/api";

const statusVariant: Record<
  string,
  "default" | "secondary" | "destructive" | "success" | "warning"
> = {
  online: "success",
  syncing: "warning",
  offline: "secondary",
  error: "destructive",
};

export default function AgentsPage() {
  const t = useTranslations("agents");
  const [showDownload, setShowDownload] = useState(false);

  const { data: agents = [], isLoading } = useQuery<Agent[]>({
    queryKey: ["agents"],
    queryFn: async () => {
      const response = await api.get("/agents");
      return Array.isArray(response.data)
        ? response.data
        : response.data.results || [];
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
          <p className="text-muted-foreground">
            {t("subtitle")}
          </p>
        </div>
        <Button onClick={() => setShowDownload(true)}>
          <Plus className="h-4 w-4 mr-2" />
          {t("addDevice")}
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="animate-pulse">
                <div className="h-5 w-32 rounded bg-muted" />
                <div className="h-4 w-48 rounded bg-muted" />
              </CardHeader>
              <CardContent className="animate-pulse space-y-2">
                <div className="h-4 w-full rounded bg-muted" />
                <div className="h-4 w-3/4 rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : agents.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12 text-muted-foreground">
            <Bot className="h-12 w-12" />
            <div className="text-center">
              <p className="text-lg font-medium">{t("noDevices")}</p>
              <p className="text-sm mt-1">
                {t("noDevicesDesc")}
              </p>
            </div>
            <Button onClick={() => setShowDownload(true)}>
              <Download className="h-4 w-4 mr-2" />
              {t("downloadEdgeDevice")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Link key={agent.id} href={`/agents/${agent.agent_id}`}>
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="rounded-md bg-muted p-2">
                        <Bot className="h-5 w-5" />
                      </div>
                      <div>
                        <CardTitle className="text-base">
                          {agent.name}
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {agent.agent_id}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge
                      variant={statusVariant[agent.status] || "secondary"}
                    >
                      {agent.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Globe className="h-3.5 w-3.5" />
                    <span>
                      {agent.platform} &middot; {agent.hostname}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Cpu className="h-3.5 w-3.5" />
                    <span>v{agent.agent_version}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <HardDrive className="h-3.5 w-3.5" />
                    <span>{t("countFiles", { count: agent.files_count })}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <FolderOpen className="h-3.5 w-3.5" />
                    <span>{t("countFolders", { count: agent.folders?.length || 0 })}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock className="h-3.5 w-3.5" />
                    <span>
                      {agent.last_seen
                        ? formatDate(agent.last_seen)
                        : t("neverSeen")}
                    </span>
                  </div>
                  {agent.capabilities && agent.capabilities.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {agent.capabilities.map((cap) => (
                        <Badge
                          key={cap}
                          variant="outline"
                          className="text-xs"
                        >
                          {cap}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <p className="text-sm text-muted-foreground">
        {t("deviceCount", { count: agents.length })}
      </p>

      <DownloadAgentDialog
        open={showDownload}
        onClose={() => setShowDownload(false)}
      />
    </div>
  );
}
