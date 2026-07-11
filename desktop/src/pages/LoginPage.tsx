import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-shell";
import { useAuthStore } from "../stores/auth-store";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
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
  const [manualUrl, setManualUrl] = useState("http://localhost:8000");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadServerConfig();
  }, [loadServerConfig]);

  useEffect(() => {
    let cancelled = false;
    let retries = 0;

    const checkHealth = async () => {
      try {
        const healthy: boolean = await invoke("agent_health");
        if (cancelled) return;
        if (healthy) {
          setStep("idle");
          setError("");
        } else if (retries < 10) {
          retries++;
          setTimeout(checkHealth, 2000);
        } else {
          setStep("idle");
          setError("Agent not responding — offline mode. Enter server URL to connect.");
        }
      } catch {
        if (cancelled) return;
        if (retries < 10) {
          retries++;
          setTimeout(checkHealth, 2000);
        } else {
          setStep("idle");
          setError("Agent not responding — offline mode. Enter server URL to connect.");
        }
      }
    };

    checkHealth();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const effectiveUrl = serverUrl || manualUrl;

  const handleLogin = async () => {
    let apiUrl = effectiveUrl;
    if (!apiUrl) return;
    if (!apiUrl.match(/^https?:\/\//)) apiUrl = `http://${apiUrl}`;

    const frontendBase = webUrl || apiUrl;
    let frontendUrl = frontendBase;
    if (!frontendUrl.match(/^https?:\/\//)) frontendUrl = `http://${frontendUrl}`;

    setStep("waiting");
    setError("");

    try {
      const port: number = await invoke("start_auth_server");
      const callbackUrl = `http://localhost:${port}/callback`;
      const loginUrl = `${frontendUrl.replace(/\/+$/, "")}/login?desktop_callback=${encodeURIComponent(callbackUrl)}`;

      await open(loginUrl);

      pollRef.current = setInterval(async () => {
        try {
          const tokens: AuthTokens | null = await invoke("poll_auth_result");
          if (tokens) {
            if (pollRef.current) clearInterval(pollRef.current);
            await invoke("stop_auth_server");

            setStep("registering");
            try {
              const result = await invoke<{ agent_id: string; api_key: string }>(
                "register_agent",
                { serverUrl: apiUrl, accessToken: tokens.access_token },
              );
              useAuthStore.getState().setAgent(result);
            } catch (regErr) {
              setError(`Device registration failed: ${String(regErr)}`);
              setStep("error");
              return;
            }

            login(apiUrl, tokens.access_token, tokens.refresh_token);
            await useAuthStore.getState().fetchUser();
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

          {step === "idle" && !effectiveUrl && (
            <div className="space-y-3">
              <Input
                placeholder="https://your-server.com"
                value={manualUrl}
                onChange={(e) => setManualUrl(e.target.value)}
              />
            </div>
          )}

          {step === "idle" && (
            <Button
              className="w-full"
              onClick={handleLogin}
              disabled={!effectiveUrl}
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
