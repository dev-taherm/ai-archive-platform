export type OSType = "linux" | "darwin" | "windows";

export function detectOS(): OSType {
  if (typeof navigator === "undefined") return "linux";
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("win")) return "windows";
  if (ua.includes("mac")) return "darwin";
  return "linux";
}

export function osLabel(os: OSType): string {
  switch (os) {
    case "linux":
      return "Linux (x86_64)";
    case "darwin":
      return "macOS (Apple Silicon / Intel)";
    case "windows":
      return "Windows (x86_64)";
  }
}

export function osFileName(os: OSType): string {
  const suffix = os === "windows" ? ".exe" : "";
  return `edge-agent-${os}-x86_64${suffix}`;
}

export function osInstallCommand(os: OSType): string {
  switch (os) {
    case "linux":
    case "darwin":
      return "chmod +x install.sh && ./install.sh";
    case "windows":
      return "install.bat";
  }
}

export function osRunCommand(os: OSType): string {
  switch (os) {
    case "linux":
    case "darwin":
      return "~/.edge-agent/edge-agent run";
    case "windows":
      return "%USERPROFILE%\\.edge-agent\\edge-agent.exe run";
  }
}
