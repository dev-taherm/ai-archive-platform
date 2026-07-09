import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-shell";
import { useAuthStore } from "../stores/auth-store";
import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { LanguageSwitcher } from "../components/LanguageSwitcher";

type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const serverUrl = useAuthStore((s) => s.serverUrl);
  const webUrl = useAuthStore((s) => s.webUrl);
  const loadServerConfig = useAuthStore((s) => s.loadServerConfig);

  const [status, setStatus] = useState<"idle" | "waiting" | "error">("idle");
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadServerConfig();
  }, [loadServerConfig]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleLogin = async () => {
    if (!serverUrl || !webUrl) return;

    setStatus("waiting");
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
            login(serverUrl, tokens.access_token);
            navigate("/dashboard");
          }
        } catch {
          // Polling error — keep trying
        }
      }, 1000);
    } catch (err) {
      setStatus("idle");
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
          {!serverUrl && (
            <p className="text-sm text-muted-foreground text-center">
              Loading server configuration...
            </p>
          )}
          <Button
            className="w-full"
            onClick={handleLogin}
            disabled={status === "waiting" || !serverUrl || !webUrl}
          >
            {status === "waiting"
              ? t("login.waiting") || "Waiting for authentication..."
              : t("login.browser") || "Login in Browser"}
          </Button>
          {status === "waiting" && (
            <div className="flex flex-col items-center gap-2 pt-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <p className="text-xs text-muted-foreground">
                A browser window has opened. Complete login there.
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
