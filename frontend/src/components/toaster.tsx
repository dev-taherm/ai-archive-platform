"use client";

import { useToastStore } from "@/hooks/use-toast";
import { X } from "lucide-react";

export function Toaster() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`rounded-lg border p-4 shadow-lg min-w-[300px] max-w-[400px] ${
            t.variant === "destructive"
              ? "border-destructive bg-destructive text-destructive-foreground"
              : "border-brand-teal/20 bg-background"
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-medium">{t.title}</p>
              {t.description && (
                <p className="text-xs opacity-80">{t.description}</p>
              )}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="shrink-0 opacity-50 hover:opacity-100"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
