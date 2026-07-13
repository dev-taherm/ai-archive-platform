"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import type { ToolCall } from "@/types/api";

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const t = useTranslations("chat");
  const tc = useTranslations("common");
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-2 border border-brand-teal/20 rounded-md text-xs">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-left hover:bg-muted/50 rounded-md"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0" />
        )}
        <Wrench className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className="font-medium">{toolCall.name}</span>
        {toolCall.result && (
          <Badge variant="outline" className="ml-auto text-[10px]">
            {tc("done")}
          </Badge>
        )}
      </button>
      {expanded && (
        <div className="px-2 pb-2 space-y-1">
          {Object.keys(toolCall.arguments).length > 0 && (
            <div>
              <span className="text-muted-foreground">{t("args")}</span>{" "}
              <code className="text-[10px] bg-muted px-1 rounded">
                {JSON.stringify(toolCall.arguments)}
              </code>
            </div>
          )}
          {toolCall.result && (
            <div>
              <span className="text-muted-foreground">{t("result")}</span>{" "}
              <span className="text-[10px]">{toolCall.result.slice(0, 500)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
