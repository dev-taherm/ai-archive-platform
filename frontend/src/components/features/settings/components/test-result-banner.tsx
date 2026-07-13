"use client";

import { CheckCircle, XCircle } from "lucide-react";

interface TestResultBannerProps {
  testResult: { ok: boolean; message: string } | null;
  t: Function;
}

export default function TestResultBanner({ testResult, t }: TestResultBannerProps) {
  if (!testResult) return null;

  return (
    <div
      className={`flex items-start gap-2 p-3 rounded-md text-sm ${
        testResult.ok
          ? "bg-green-500/10 text-green-600 dark:text-green-400"
          : "bg-red-500/10 text-red-600 dark:text-red-400"
      }`}
    >
      {testResult.ok ? (
        <CheckCircle className="h-4 w-4 mt-0.5 shrink-0" />
      ) : (
        <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
      )}
      <span>{testResult.message}</span>
    </div>
  );
}
