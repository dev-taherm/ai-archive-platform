"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, Wrench, Copy, Check } from "lucide-react";

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

function SimpleMarkdown({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const renderInline = (text: string) => {
    const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[([^\]]+)\]\(([^)]+)\))/g);
    return parts.map((part, i) => {
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code key={i} className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono">
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("*") && part.endsWith("*") && !part.startsWith("**")) {
        return <em key={i}>{part.slice(1, -1)}</em>;
      }
      const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        return (
          <a key={i} href={linkMatch[2]} target="_blank" rel="noopener noreferrer" className="text-primary underline">
            {linkMatch[1]}
          </a>
        );
      }
      return part;
    });
  };

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeContent = "";
  let codeLang = "";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("```")) {
      if (inCodeBlock) {
        elements.push(
          <div key={`code-${i}`} className="my-2 rounded-lg overflow-hidden border bg-muted/50">
            <div className="flex items-center justify-between px-3 py-1 text-xs text-muted-foreground border-b">
              <span>{codeLang || "code"}</span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(codeContent);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="flex items-center gap-1 hover:text-foreground"
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <pre className="p-3 text-xs overflow-x-auto">
              <code>{codeContent}</code>
            </pre>
          </div>
        );
        codeContent = "";
        codeLang = "";
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent += (codeContent ? "\n" : "") + line;
      continue;
    }

    if (line.startsWith("### ")) {
      elements.push(
        <h3 key={i} className="text-sm font-semibold mt-3 mb-1">
          {renderInline(line.slice(4))}
        </h3>
      );
    } else if (line.startsWith("## ")) {
      elements.push(
        <h2 key={i} className="text-base font-semibold mt-4 mb-2">
          {renderInline(line.slice(3))}
        </h2>
      );
    } else if (line.startsWith("# ")) {
      elements.push(
        <h1 key={i} className="text-lg font-bold mt-4 mb-2">
          {renderInline(line.slice(2))}
        </h1>
      );
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <li key={i} className="ml-4 list-disc text-sm">
          {renderInline(line.slice(2))}
        </li>
      );
    } else if (/^\d+\.\s/.test(line)) {
      const match = line.match(/^(\d+)\.\s(.*)$/);
      if (match) {
        elements.push(
          <li key={i} className="ml-4 list-decimal text-sm">
            {renderInline(match[2])}
          </li>
        );
      }
    } else if (line.startsWith("> ")) {
      elements.push(
        <blockquote key={i} className="border-l-2 border-primary/30 pl-3 text-sm text-muted-foreground italic">
          {renderInline(line.slice(2))}
        </blockquote>
      );
    } else if (line.startsWith("---")) {
      elements.push(<hr key={i} className="my-2 border-border" />);
    } else if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
    } else {
      elements.push(
        <p key={i} className="text-sm leading-relaxed">
          {renderInline(line)}
        </p>
      );
    }
  }

  return <div className="space-y-1">{elements}</div>;
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
        className={`max-w-[85%] p-3 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <SimpleMarkdown content={message.content} />
        )}
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
