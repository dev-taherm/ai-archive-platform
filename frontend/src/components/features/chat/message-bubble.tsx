"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ document_id: string; title: string; snippet: string }>;
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <Card
        className={`max-w-[80%] p-3 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border/50">
            <p className="text-xs font-medium mb-1">Sources:</p>
            <div className="flex flex-wrap gap-1">
              {message.sources.map((src, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {src.title || "Document"}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
