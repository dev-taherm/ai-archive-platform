"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Download,
  Monitor,
  Terminal,
  CheckCircle2,
  Loader2,
  Copy,
  ExternalLink,
  ChevronDown,
  Bot,
  Wifi,
} from "lucide-react";
import api from "@/lib/api";
import { detectOS, osLabel, osRunCommand, type OSType } from "@/lib/detect-os";
import type { AgentSetupResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface DownloadAgentDialogProps {
  open: boolean;
  onClose: () => void;
}

type Step = "creating" | "download" | "instructions" | "waiting" | "connected";

export function DownloadAgentDialog({ open, onClose }: DownloadAgentDialogProps) {
  const [step, setStep] = useState<Step>("creating");
  const [selectedOS, setSelectedOS] = useState<OSType>("linux");
  const [agentData, setAgentData] = useState<AgentSetupResponse | null>(null);
  const [showAllOS, setShowAllOS] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setSelectedOS(detectOS());
  }, []);

  const setupMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<AgentSetupResponse>("/agents/setup", {
        name: `Edge Agent (${navigator.platform})`,
        platform: detectOS(),
        hostname: navigator.userAgent.split(" ").pop() || "",
      });
      return res.data;
    },
    onSuccess: (data) => {
      setAgentData(data);
      setStep("download");
    },
  });

  // Auto-create agent on open
  useEffect(() => {
    if (open && step === "creating" && !agentData) {
      setupMutation.mutate();
    }
  }, [open]);

  // Poll agent status when waiting
  const { data: agentStatus } = useQuery({
    queryKey: ["agents", agentData?.agent_id],
    queryFn: async () => {
      const res = await api.get(`/agents/${agentData!.agent_id}`);
      return res.data;
    },
    enabled: step === "waiting" && !!agentData?.agent_id,
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (agentStatus?.status === "online") {
      setStep("connected");
    }
  }, [agentStatus]);

  const handleDownload = useCallback(async () => {
    if (!agentData) return;
    setDownloading(true);
    try {
      const res = await api.get(
        `${agentData.download_url}?os=${selectedOS}&api_key=${encodeURIComponent(agentData.api_key)}`,
        { responseType: "blob" },
      );
      const blob = new Blob([res.data], { type: "application/zip" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "edge-agent.zip";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setStep("instructions");
    } catch (err) {
      console.error("Download failed:", err);
    } finally {
      setDownloading(false);
    }
  }, [agentData, selectedOS]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (!open) return null;

  const allOS: OSType[] = ["linux", "darwin", "windows"];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Bot className="h-6 w-6 text-primary" />
              </div>
              <div>
                <CardTitle>Set Up Edge Agent</CardTitle>
                <CardDescription>
                  Download and install the agent to start processing documents
                </CardDescription>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Skip for now
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step: Creating */}
          {step === "creating" && (
            <div className="flex flex-col items-center py-8 gap-4">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Setting up your agent...</p>
            </div>
          )}

          {/* Step: Download */}
          {step === "download" && (
            <div className="space-y-4">
              <div className="text-center py-4">
                <Download className="h-12 w-12 mx-auto text-primary mb-3" />
                <h3 className="text-lg font-semibold">
                  Download for {osLabel(selectedOS)}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  The agent will be configured automatically with your API key
                </p>
              </div>

              <div className="flex justify-center">
                <Button
                  size="lg"
                  onClick={handleDownload}
                  disabled={downloading}
                  className="px-8"
                >
                  {downloading ? (
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <Download className="h-5 w-5 mr-2" />
                  )}
                  {downloading ? "Downloading..." : "Download Edge Agent"}
                </Button>
              </div>

              <div className="text-center">
                <button
                  onClick={() => setShowAllOS(!showAllOS)}
                  className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 mx-auto"
                >
                  Other platforms
                  <ChevronDown
                    className={`h-3 w-3 transition-transform ${showAllOS ? "rotate-180" : ""}`}
                  />
                </button>
                {showAllOS && (
                  <div className="flex justify-center gap-2 mt-3">
                    {allOS.map((os) => (
                      <Button
                        key={os}
                        variant={os === selectedOS ? "default" : "outline"}
                        size="sm"
                        onClick={() => setSelectedOS(os)}
                      >
                        {os === "linux" && <Terminal className="h-3 w-3 mr-1" />}
                        {os === "darwin" && <Monitor className="h-3 w-3 mr-1" />}
                        {os === "windows" && <Monitor className="h-3 w-3 mr-1" />}
                        {osLabel(os)}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step: Instructions */}
          {step === "instructions" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                <span className="font-medium">Download started</span>
              </div>

              <div className="bg-muted rounded-lg p-4 space-y-3">
                <h4 className="font-medium text-sm">Installation Steps</h4>

                {selectedOS === "windows" ? (
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Extract the zip to a folder of your choice</li>
                    <li>
                      Run{" "}
                      <code className="bg-background px-1 rounded">
                        install.bat
                      </code>{" "}
                      (double-click or in Command Prompt)
                    </li>
                    <li>
                      Start the agent:
                      <div className="relative mt-1">
                        <code className="block bg-background p-2 rounded text-xs">
                          %USERPROFILE%\.edge-agent\edge-agent.exe run
                        </code>
                        <button
                          onClick={() =>
                            copyToClipboard(
                              "%USERPROFILE%\\.edge-agent\\edge-agent.exe run"
                            )
                          }
                          className="absolute right-2 top-2 p-1 hover:bg-muted rounded"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                    </li>
                  </ol>
                ) : (
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Extract the zip:</li>
                    <div className="relative">
                      <code className="block bg-background p-2 rounded text-xs">
                        unzip edge-agent.zip -d edge-agent
                      </code>
                      <button
                        onClick={() =>
                          copyToClipboard("unzip edge-agent.zip -d edge-agent")
                        }
                        className="absolute right-2 top-2 p-1 hover:bg-muted rounded"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                    </div>
                    <li>Run the installer:</li>
                    <div className="relative">
                      <code className="block bg-background p-2 rounded text-xs">
                        cd edge-agent && chmod +x install.sh && ./install.sh
                      </code>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            "cd edge-agent && chmod +x install.sh && ./install.sh"
                          )
                        }
                        className="absolute right-2 top-2 p-1 hover:bg-muted rounded"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                    </div>
                    <li>Start the agent:</li>
                    <div className="relative">
                      <code className="block bg-background p-2 rounded text-xs">
                        ~/.edge-agent/edge-agent run
                      </code>
                      <button
                        onClick={() =>
                          copyToClipboard("~/.edge-agent/edge-agent run")
                        }
                        className="absolute right-2 top-2 p-1 hover:bg-muted rounded"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                    </div>
                  </ol>
                )}
              </div>

              <div className="flex justify-center">
                <Button onClick={() => setStep("waiting")}>
                  <Wifi className="h-4 w-4 mr-2" />
                  I&apos;ve started the agent
                </Button>
              </div>
            </div>
          )}

          {/* Step: Waiting for connection */}
          {step === "waiting" && (
            <div className="flex flex-col items-center py-8 gap-4">
              <div className="relative">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                <Wifi className="h-5 w-5 absolute bottom-0 right-0 text-primary animate-pulse" />
              </div>
              <h3 className="text-lg font-semibold">
                Waiting for agent to connect...
              </h3>
              <p className="text-sm text-muted-foreground text-center max-w-md">
                Make sure the agent is running. It should connect within a few
                seconds.
              </p>
              <Badge variant="secondary" className="animate-pulse">
                Agent ID: {agentData?.agent_id}
              </Badge>
            </div>
          )}

          {/* Step: Connected */}
          {step === "connected" && (
            <div className="flex flex-col items-center py-8 gap-4">
              <div className="p-3 bg-green-500/10 rounded-full">
                <CheckCircle2 className="h-12 w-12 text-green-500" />
              </div>
              <h3 className="text-lg font-semibold text-green-600">
                Agent Connected!
              </h3>
              <p className="text-sm text-muted-foreground text-center">
                Your edge agent is now online and ready to process documents.
              </p>
              <Button onClick={onClose}>Go to Dashboard</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
