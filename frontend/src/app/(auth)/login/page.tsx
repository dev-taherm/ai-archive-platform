"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useAuthStore } from "@/stores/auth-store";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function LoginPage() {
  const searchParams = useSearchParams();
  const desktopCallback = searchParams.get("desktop_callback");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [desktopError, setDesktopError] = useState("");
  const { login, isLoggingIn, loginError } = useAuth();
  const { isAuthenticated, accessToken, refreshToken } = useAuthStore();
  const [desktopRedirecting, setDesktopRedirecting] = useState(false);

  useEffect(() => {
    if (desktopCallback && isAuthenticated && accessToken && refreshToken) {
      setDesktopRedirecting(true);
      window.location.href = `${desktopCallback}?access_token=${encodeURIComponent(accessToken)}&refresh_token=${encodeURIComponent(refreshToken)}`;
    }
  }, [desktopCallback, isAuthenticated, accessToken, refreshToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (desktopCallback) {
      setDesktopError("");
      try {
        const response = await api.post<{ access: string; refresh: string }>(
          "/auth/login",
          { email, password }
        );
        const { access, refresh } = response.data;
        window.location.href = `${desktopCallback}?access_token=${encodeURIComponent(access)}&refresh_token=${encodeURIComponent(refresh)}`;
      } catch (err: any) {
        setDesktopError(
          err?.response?.data?.detail
            || err?.response?.data?.email
            || "Invalid credentials"
        );
      }
      return;
    }

    login({ email, password });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {desktopCallback ? "Authenticate Desktop App" : "Sign in"}
        </CardTitle>
        <CardDescription>
          {desktopCallback
            ? "Log in to connect your desktop application."
            : "Enter your credentials to access your account"}
        </CardDescription>
      </CardHeader>
      {desktopCallback && desktopRedirecting ? (
        <CardContent className="flex flex-col items-center space-y-4 py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Connecting desktop app...</p>
        </CardContent>
      ) : (
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {desktopCallback && desktopError && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {desktopError}
            </div>
          )}
          {!desktopCallback && loginError && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {(loginError as any)?.response?.data?.detail
                || (loginError as any)?.response?.data?.email
                || "Invalid credentials"}
            </div>
          )}
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              Email
            </label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              Password
            </label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" disabled={isLoggingIn}>
            {isLoggingIn ? "Signing in..." : "Sign in"}
          </Button>
          {!desktopCallback && (
            <p className="text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-primary hover:underline">
                Sign up
              </Link>
            </p>
          )}
        </CardFooter>
      </form>
      )}
    </Card>
  );
}
