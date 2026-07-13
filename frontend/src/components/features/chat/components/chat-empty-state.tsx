"use client";

import { Sparkles } from "lucide-react";

interface ChatEmptyStateProps {
  starterPrompts: string[];
  onSend: (text: string) => void;
  t: Function;
}

export default function ChatEmptyState({
  starterPrompts,
  onSend,
  t,
}: ChatEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
      <div className="space-y-2">
        <div className="flex items-center justify-center gap-2 text-2xl font-semibold">
          <Sparkles className="h-6 w-6 text-primary" />
          {t("aiAssistant")}
        </div>
        <p className="text-muted-foreground max-w-md">
          {t("emptyDescription")}
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
        {starterPrompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onSend(prompt)}
            className="text-left p-3 rounded-lg border bg-card hover:bg-muted text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
