"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Download,
  Monitor,
  Terminal,
  CheckCircle2,
  Loader2,
  Copy,
  ChevronDown,
  Bot,
} from "lucide-react";
import api from "@/lib/api";
import { detectOS, osLabel, type OSType } from "@/lib/detect-os";
import type { DesktopBuildManifest } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface DownloadAgentDialogProps {
  open: boolean;
  onClose: () => void;
}

type Step = "download" | "instructions" | "done";

export function DownloadAgentDialog({ open, onClose }: DownloadAgentDialogProps) {
  const [step, setStep] = useState<Step>("download");
  const [selectedOS, setSelectedOS] = useState<OSType>("linux");
  const [showAllOS, setShowAllOS] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setSelectedOS(detectOS());
  }, []);

  // Fetch desktop manifest to know which platforms are available
  const { data: manifest } = useQuery({
    queryKey: ["agents", "desktop-manifest"],
    queryFn: async () => {
      const res = await api.get<DesktopBuildManifest>("/agents/desktop-manifest");
      return res.data;
    },
  });

  const isOSAvailable = (os: OSType): boolean => {
    if (!manifest?.builds) return false;
    if (os === "linux") return "linux-x86_64" in manifest.builds;
    if (os === "darwin") return "darwin-arm64" in manifest.builds || "darwin-x86_64" in manifest.builds;
    if (os === "windows") return "windows-x86_64" in manifest.builds;
    return false;
  };

  const handleDownload = useCallback(async () => {
    setDownloading(true);
    try {
      const res = await api.get(
        `/agents/download-desktop?os=${selectedOS}`,
        { responseType: "blob" },
      );
      const blob = new Blob([res.data], { type: "application/zip" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `basirah-desktop-${selectedOS}.zip`;
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
  }, [selectedOS]);

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
                <CardTitle>Download Basirah Desktop</CardTitle>
                <CardDescription>
                  Install the desktop app to start processing documents
                </CardDescription>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Skip for now
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step: Download */}
          {step === "download" && (
            <div className="space-y-4">
              <div className="text-center py-4">
                <Download className="h-12 w-12 mx-auto text-primary mb-3" />
                <h3 className="text-lg font-semibold">
                  Download for {osLabel(selectedOS)}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  The server URL is pre-configured — just install and log in
                </p>
              </div>

              <div className="flex justify-center">
                <Button
                  size="lg"
                  onClick={handleDownload}
                  disabled={downloading || !isOSAvailable(selectedOS)}
                  className="px-8"
                >
                  {downloading ? (
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <Download className="h-5 w-5 mr-2" />
                  )}
                  {downloading ? "Downloading..." : "Download Basirah Desktop"}
                </Button>
              </div>

              {!isOSAvailable(selectedOS) && manifest?.builds && Object.keys(manifest.builds).length > 0 && (
                <p className="text-center text-sm text-muted-foreground">
                  Desktop app not yet available for {osLabel(selectedOS)}
                </p>
              )}

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
                        disabled={!isOSAvailable(os)}
                      >
                        {os === "linux" && <Terminal className="h-3 w-3 mr-1" />}
                        {os === "darwin" && <Monitor className="h-3 w-3 mr-1" />}
                        {os === "windows" && <Monitor className="h-3 w-3 mr-1" />}
                        {osLabel(os)}
                        {!isOSAvailable(os) && " (coming soon)"}
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
                    <li>Open <strong>Basirah Desktop</strong> from your Start Menu</li>
                    <li>Log in with your email and password</li>
                  </ol>
                ) : (
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Extract the zip:</li>
                    <div className="relative">
                      <code className="block bg-background p-2 rounded text-xs">
                        unzip basirah-desktop.zip -d basirah-desktop
                      </code>
                      <button
                        onClick={() =>
                          copyToClipboard("unzip basirah-desktop.zip -d basirah-desktop")
                        }
                        className="absolute right-2 top-2 p-1 hover:bg-muted rounded"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                    </div>
                    <li>Run the installer:</li>
                    <div className="relative">
                      <code className="block bg-background p-2 rounded text-xs">
                        cd basirah-desktop && chmod +x install.sh && ./install.sh
                      </code>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            "cd basirah-desktop && chmod +x install.sh && ./install.sh"
                          )
                        }
                        className="absolute right-2 top-2 p-1 hover:bg-muted rounded"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                    </div>
                    <li>Open <strong>Basirah Desktop</strong> from your applications</li>
                    <li>Log in with your email and password</li>
                  </ol>
                )}
              </div>

              <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
                <p className="text-sm text-primary">
                  The server URL is pre-configured. You only need to enter your email and password.
                </p>
              </div>

              <div className="flex justify-center">
                <Button onClick={() => setStep("done")}>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Got it
                </Button>
              </div>
            </div>
          )}

          {/* Step: Done */}
          {step === "done" && (
            <div className="flex flex-col items-center py-8 gap-4">
              <div className="p-3 bg-green-500/10 rounded-full">
                <CheckCircle2 className="h-12 w-12 text-green-500" />
              </div>
              <h3 className="text-lg font-semibold text-green-600">
                You&apos;re all set!
              </h3>
              <p className="text-sm text-muted-foreground text-center max-w-md">
                Install Basirah Desktop, open it, and log in with your email and password.
                The server URL is already configured.
              </p>
              <Button onClick={onClose}>Go to Dashboard</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
