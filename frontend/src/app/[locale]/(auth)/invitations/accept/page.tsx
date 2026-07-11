"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Archive, Check, AlertCircle } from "lucide-react";

export default function InvitationAcceptPage() {
  const t = useTranslations("auth");
  const tc = useTranslations("common");
  const searchParams = useSearchParams();
  const router = useRouter();
  const { register, isAuthenticated, isRegistering, registerError } = useAuth();

  const token = searchParams.get("token");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [success, setSuccess] = useState(false);

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30">
        <div className="w-full max-w-md space-y-6 rounded-lg border bg-card p-8 text-center shadow-sm">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h1 className="text-xl font-bold">{t("invalidInvitation")}</h1>
          <p className="text-muted-foreground">
            {t("invalidInvitationDesc")}
          </p>
          <Button onClick={() => router.push("/login")} className="w-full">
            {t("goToLogin")}
          </Button>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30">
        <div className="w-full max-w-md space-y-6 rounded-lg border bg-card p-8 text-center shadow-sm">
          <Check className="mx-auto h-12 w-12 text-green-500" />
          <h1 className="text-xl font-bold">{t("alreadySignedIn")}</h1>
          <p className="text-muted-foreground">
            {t("alreadySignedInDesc")}
          </p>
          <Button onClick={() => router.push("/dashboard")} className="w-full">
            {tc("goToDashboard")}
          </Button>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30">
        <div className="w-full max-w-md space-y-6 rounded-lg border bg-card p-8 text-center shadow-sm">
          <Check className="mx-auto h-12 w-12 text-green-500" />
          <h1 className="text-xl font-bold">{t("welcome")}</h1>
          <p className="text-muted-foreground">
            {t("accountCreated")}
          </p>
          <Button onClick={() => router.push("/dashboard")} className="w-full">
            {tc("goToDashboard")}
          </Button>
        </div>
      </div>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    register({
      email,
      username,
      password,
      password_confirm: passwordConfirm,
      first_name: firstName || undefined,
      last_name: lastName || undefined,
      invitation_token: token,
    });
    setSuccess(true);
  };

  const getFieldError = (field: string): string | null => {
    if (!registerError) return null;
    const err = registerError as any;
    if (err?.response?.data?.[field]) {
      return Array.isArray(err.response.data[field])
        ? err.response.data[field][0]
        : err.response.data[field];
    }
    return null;
  };

  const getGeneralError = (): string | null => {
    if (!registerError) return null;
    const err = registerError as any;
    return err?.response?.data?.detail || err?.message || null;
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30">
      <div className="w-full max-w-md space-y-6 rounded-lg border bg-card p-8 shadow-sm">
        <div className="space-y-2 text-center">
          <div className="flex justify-center">
            <Archive className="h-10 w-10 text-primary" />
          </div>
          <h1 className="text-xl font-bold">{t("acceptInvitation")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("joinOrganization")}
          </p>
        </div>

        {getGeneralError() && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {getGeneralError()}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              {t("email")}
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            {getFieldError("email") && (
              <p className="text-xs text-destructive">{getFieldError("email")}</p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="username" className="text-sm font-medium">
              {t("username")}
            </label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            {getFieldError("username") && (
              <p className="text-xs text-destructive">{getFieldError("username")}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="firstName" className="text-sm font-medium">
                {t("firstName")}
              </label>
              <Input
                id="firstName"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="lastName" className="text-sm font-medium">
                {t("lastName")}
              </label>
              <Input
                id="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              {t("password")}
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
            {getFieldError("password") && (
              <p className="text-xs text-destructive">{getFieldError("password")}</p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="passwordConfirm" className="text-sm font-medium">
              {t("confirmPassword")}
            </label>
            <Input
              id="passwordConfirm"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              minLength={8}
            />
            {getFieldError("password_confirm") && (
              <p className="text-xs text-destructive">{getFieldError("password_confirm")}</p>
            )}
          </div>

          {getFieldError("invitation_token") && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {getFieldError("invitation_token")}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={isRegistering}>
            {isRegistering ? t("creatingAccount") : t("createAccountAndJoin")}
          </Button>
        </form>
      </div>
    </div>
  );
}
