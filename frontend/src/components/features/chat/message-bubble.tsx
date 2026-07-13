"use client";

import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Wrench } from "lucide-react";
import SimpleMarkdown from "./components/simple-markdown";
import ToolCallCard from "./components/tool-call-card";

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ document_id: string; title: string; snippet: string }>;
  tool_calls?: ToolCall[];
}

export default function MessageBubble({ message }: { message: Message }) {
  const t = useTranslations("chat");
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <Card className={`max-w-[85%] p-3 ${isUser ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <SimpleMarkdown content={message.content} />
        )}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2 pt-2 border-t border-brand-teal/20">
            <p className="text-xs font-medium mb-1 flex items-center gap-1">
              <Wrench className="h-3 w-3 text-brand-teal" />
              {t("toolsUsed")}
            </p>
            {message.tool_calls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-brand-teal/20">
            <p className="text-xs font-medium mb-1">{t("sources")}</p>
            <div className="flex flex-wrap gap-1">
              {message.sources.map((src, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {src.title || t("document")}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
