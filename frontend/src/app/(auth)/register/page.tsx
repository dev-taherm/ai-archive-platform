"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
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

function getFieldErrors(error: any, field: string): string[] {
  if (!error?.response?.data) return [];
  const data = error.response.data;
  const val = data[field];
  if (Array.isArray(val)) return val;
  if (typeof val === "string") return [val];
  return [];
}

function getGeneralError(error: any): string {
  if (!error?.response?.data) return "";
  const data = error.response.data;
  if (data.detail) return data.detail;
  if (data.non_field_errors) {
    return Array.isArray(data.non_field_errors) ? data.non_field_errors.join(". ") : data.non_field_errors;
  }
  return "";
}

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { register, isRegistering, registerError } = useAuth();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) return;
    register({ email, password, password_confirm: confirmPassword, username });
  };

  const passwordMismatch = password !== confirmPassword && confirmPassword;
  const usernameErrors = getFieldErrors(registerError, "username");
  const emailErrors = getFieldErrors(registerError, "email");
  const passwordErrors = getFieldErrors(registerError, "password");
  const confirmPasswordErrors = getFieldErrors(registerError, "password_confirm");
  const generalError = getGeneralError(registerError);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create an account</CardTitle>
        <CardDescription>
          Enter your information to get started
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {generalError && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {generalError}
            </div>
          )}
          {passwordMismatch && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              Passwords do not match
            </div>
          )}
          <div className="space-y-2">
            <label htmlFor="username" className="text-sm font-medium">
              Username
            </label>
            <Input
              id="username"
              placeholder="johndoe"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            {usernameErrors.map((err, i) => (
              <p key={i} className="text-xs text-destructive">{err}</p>
            ))}
          </div>
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
            {emailErrors.map((err, i) => (
              <p key={i} className="text-xs text-destructive">{err}</p>
            ))}
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
              minLength={8}
            />
            {passwordErrors.map((err, i) => (
              <p key={i} className="text-xs text-destructive">{err}</p>
            ))}
          </div>
          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium">
              Confirm Password
            </label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
            />
            {confirmPasswordErrors.map((err, i) => (
              <p key={i} className="text-xs text-destructive">{err}</p>
            ))}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" disabled={isRegistering}>
            {isRegistering ? "Creating account..." : "Create account"}
          </Button>
          <p className="text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
