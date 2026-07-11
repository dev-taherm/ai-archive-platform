"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import MessageBubble from "./message-bubble";
import {
  Plus,
  MessageSquare,
  Trash2,
  Loader2,
  Send,
  Sparkles,
} from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ document_id: string; title: string; snippet: string }>;
  tool_calls?: Array<{
    id: string;
    name: string;
    arguments: Record<string, unknown>;
    result?: string;
  }>;
}

interface Session {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export default function ChatInterface() {
  const t = useTranslations("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const starterPrompts = useMemo(
    () => [t("starter1"), t("starter2"), t("starter3"), t("starter4"), t("starter5")],
    [t]
  );

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadSessions = async () => {
    try {
      const res = await api.get("/chat/sessions", { params: { limit: 50 } });
      setSessions(res.data.sessions || []);
    } catch {
      // ignore
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadSessionMessages = async (sid: string) => {
    setSessionId(sid);
    setMessages([]);
    try {
      const res = await api.get(`/chat/sessions/${sid}/messages`, {
        params: { limit: 100 },
      });
      const raw = Array.isArray(res.data) ? res.data : res.data.messages || [];
      const loaded: Message[] = raw.map((m: Record<string, unknown>) => ({
        id: m.id as string,
        role: m.role as "user" | "assistant",
        content: m.content as string,
        sources: m.sources as Message["sources"],
        tool_calls: m.tool_calls as Message["tool_calls"],
      }));
      setMessages(loaded);
    } catch {
      // ignore
    }
  };

  const createNewSession = () => {
    setSessionId(null);
    setMessages([]);
  };

  const deleteSession = async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/chat/sessions/${sid}`);
      setSessions((prev) => prev.filter((s) => s.id !== sid));
      if (sessionId === sid) {
        createNewSession();
      }
    } catch {
      // ignore
    }
  };

  const sendMessage = async (text?: string) => {
    const msg = text || input;
    if (!msg.trim() || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: msg,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      let sid = sessionId;
      if (!sid) {
        const sessionRes = await api.post("/chat/sessions", {
          title: msg.slice(0, 100),
        });
        sid = sessionRes.data.id;
        setSessionId(sid);
        loadSessions();
      }

      const res = await api.post(`/chat/sessions/${sid}/messages`, {
        message: msg,
      });
      const assistantMessage: Message = {
        id: res.data.message?.id || crypto.randomUUID(),
        role: "assistant",
        content:
          res.data.message?.content ||
          res.data.assistant_message ||
          t("noResponse"),
        sources: res.data.message?.sources,
        tool_calls: res.data.message?.tool_calls,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      loadSessions();
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: t("errorResponse"),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Session Sidebar */}
      {sidebarOpen && (
        <div className="w-72 border-r bg-card flex flex-col shrink-0">
          <div className="p-3 border-b">
            <Button
              onClick={createNewSession}
              className="w-full justify-start gap-2"
              variant="outline"
            >
              <Plus className="h-4 w-4" />
              {t("newConversation")}
            </Button>
          </div>
          <div className="flex-1 overflow-auto p-2 space-y-1">
            {sessionsLoading ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin mr-2 text-brand-teal" />
                {t("loading")}
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center text-muted-foreground text-sm py-8">
                {t("noConversations")}
              </div>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => loadSessionMessages(session.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-left text-sm transition-colors group ${
                    sessionId === session.id
                      ? "bg-brand-teal/10 text-brand-teal"
                      : "hover:bg-muted text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <MessageSquare className="h-4 w-4 shrink-0" />
                  <span className="truncate flex-1">{session.title}</span>
                  <button
                    onClick={(e) => deleteSession(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-destructive/20 rounded"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toggle Sidebar Button */}
        <div className="p-2 border-b flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <MessageSquare className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium text-muted-foreground">
            {sessionId ? t("conversation") : t("newChat")}
          </span>
        </div>

        {/* Messages */}
        <CardContent className="flex-1 overflow-auto p-4 space-y-4 min-h-0">
          {messages.length === 0 && (
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
                    onClick={() => sendMessage(prompt)}
                    className="text-left p-3 rounded-lg border bg-card hover:bg-muted text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-4 py-2 text-sm flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-brand-teal" />
                {t("thinking")}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </CardContent>

        {/* Input */}
        <div className="p-4 border-t">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t("inputPlaceholder")}
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
