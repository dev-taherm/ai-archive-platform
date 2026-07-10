"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, ArrowRight, Download, X } from "lucide-react";
import api from "@/lib/api";
import { DownloadAgentDialog } from "@/components/features/agents/download-agent-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface OnboardingModalProps {
  open: boolean;
  onClose: () => void;
}

export function OnboardingModal({ open, onClose }: OnboardingModalProps) {
  const [showDownload, setShowDownload] = useState(false);

  // Check if user has any agents
  const { data: agents } = useQuery({
    queryKey: ["agents"],
    queryFn: async () => {
      const res = await api.get("/agents");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
  });

  const hasAgents = agents && agents.length > 0;

  // Auto-close if user already has agents
  useEffect(() => {
    if (hasAgents) {
      onClose();
    }
  }, [hasAgents, onClose]);

  if (!open || hasAgents) return null;

  if (showDownload) {
    return (
      <DownloadAgentDialog
        open={true}
        onClose={() => {
          setShowDownload(false);
          onClose();
        }}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg mx-4">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Bot className="h-6 w-6 text-primary" />
              </div>
              <div>
                <CardTitle>Welcome to AI Archive Platform</CardTitle>
                <CardDescription>
                  Let&apos;s get you started with your first edge device
                </CardDescription>
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-muted rounded-lg p-4 space-y-3">
            <h3 className="font-medium">What is an Edge Device?</h3>
            <p className="text-sm text-muted-foreground">
              The Edge Device runs on your computer and automatically processes
              documents — extracting text, classifying content, and syncing
              everything to the platform.
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-3 text-sm">
              <div className="p-1 bg-primary/10 rounded">
                <ArrowRight className="h-3 w-3 text-primary" />
              </div>
              <span>Detects and processes new documents automatically</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className="p-1 bg-primary/10 rounded">
                <ArrowRight className="h-3 w-3 text-primary" />
              </div>
              <span>Runs OCR, text extraction, and entity detection locally</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className="p-1 bg-primary/10 rounded">
                <ArrowRight className="h-3 w-3 text-primary" />
              </div>
              <span>Syncs structured data to the platform for search and chat</span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose}>
              Skip for now
            </Button>
            <Button onClick={() => setShowDownload(true)}>
              <Download className="h-4 w-4 mr-2" />
              Set Up Device
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
