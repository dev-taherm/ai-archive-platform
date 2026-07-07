"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";

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

function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-2 border border-border/50 rounded-md text-xs">
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
            done
          </Badge>
        )}
      </button>
      {expanded && (
        <div className="px-2 pb-2 space-y-1">
          {Object.keys(toolCall.arguments).length > 0 && (
            <div>
              <span className="text-muted-foreground">Args:</span>{" "}
              <code className="text-[10px] bg-muted px-1 rounded">
                {JSON.stringify(toolCall.arguments)}
              </code>
            </div>
          )}
          {toolCall.result && (
            <div>
              <span className="text-muted-foreground">Result:</span>{" "}
              <span className="text-[10px]">{toolCall.result.slice(0, 500)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
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
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border/50">
            <p className="text-xs font-medium mb-1 flex items-center gap-1">
              <Wrench className="h-3 w-3" />
              Tools used:
            </p>
            {message.tool_calls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}
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
