import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-shell";
import { useAuthStore } from "../stores/auth-store";
import { agentApi } from "../lib/agent-api";
import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { LanguageSwitcher } from "../components/LanguageSwitcher";

type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

type LoginStep = "checking-agent" | "idle" | "waiting" | "registering" | "error";

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const serverUrl = useAuthStore((s) => s.serverUrl);
  const webUrl = useAuthStore((s) => s.webUrl);
  const loadServerConfig = useAuthStore((s) => s.loadServerConfig);

  const [step, setStep] = useState<LoginStep>("checking-agent");
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadServerConfig();
  }, [loadServerConfig]);

  // Check agent sidecar health on mount
  useEffect(() => {
    if (!serverUrl) return;
    let cancelled = false;
    const checkHealth = async () => {
      try {
        const startError: string | null = await invoke("get_agent_start_error");
        if (startError) {
          if (!cancelled) {
            setError("Agent binary not found. Please reinstall Basirah Desktop.");
            setStep("error");
          }
          return;
        }
        const healthy: boolean = await invoke("agent_health");
        if (!cancelled) {
          setStep(healthy ? "idle" : "error");
          if (!healthy) setError("Agent is not responding. Please restart the application.");
        }
      } catch {
        if (!cancelled) {
          setError("Agent is not running. Please restart the application.");
          setStep("error");
        }
      }
    };
    checkHealth();
    return () => { cancelled = true; };
  }, [serverUrl]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleLogin = async () => {
    if (!serverUrl || !webUrl) return;

    setStep("waiting");
    setError("");

    try {
      const port: number = await invoke("start_auth_server");
      const callbackUrl = `http://localhost:${port}/callback`;
      const loginUrl = `${webUrl}/login?desktop_callback=${encodeURIComponent(callbackUrl)}`;

      await open(loginUrl);

      pollRef.current = setInterval(async () => {
        try {
          const tokens: AuthTokens | null = await invoke("poll_auth_result");
          if (tokens) {
            if (pollRef.current) clearInterval(pollRef.current);
            await invoke("stop_auth_server");

            // Register the agent sidecar with the backend
            setStep("registering");
            try {
              await agentApi.register(tokens.access_token, serverUrl);
            } catch (regErr) {
              setError(`Agent registration failed: ${String(regErr)}`);
              setStep("error");
              return;
            }

            // Store tokens and proceed
            login(serverUrl, tokens.access_token, tokens.refresh_token);
            navigate("/dashboard");
          }
        } catch {
          // Polling error — keep trying
        }
      }, 1000);
    } catch (err) {
      setStep("idle");
      setError(String(err) || t("login.error"));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <div className="absolute top-4 end-4">
        <LanguageSwitcher />
      </div>

      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">{t("login.title")}</CardTitle>
          <CardDescription>{t("login.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}
          {step === "checking-agent" && (
            <div className="flex flex-col items-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">Checking agent...</p>
            </div>
          )}
          {step === "error" && (
            <Button className="w-full" onClick={() => { setStep("checking-agent"); setError(""); }}>
              Retry
            </Button>
          )}
          {step === "idle" && (
            <Button
              className="w-full"
              onClick={handleLogin}
              disabled={!serverUrl || !webUrl}
            >
              {t("login.browser") || "Login in Browser"}
            </Button>
          )}
          {step === "waiting" && (
            <div className="flex flex-col items-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">
                A browser window has opened. Complete login there.
              </p>
            </div>
          )}
          {step === "registering" && (
            <div className="flex flex-col items-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">
                Registering agent with server...
              </p>
            </div>
          )}
          <p className="text-center text-xs text-muted-foreground">
            {t("login.offline")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
