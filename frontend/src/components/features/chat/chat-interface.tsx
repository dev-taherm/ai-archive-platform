"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { CardContent } from "@/components/ui/card";
import api from "@/lib/api";
import MessageBubble from "./message-bubble";
import SessionSidebar from "./components/session-sidebar";
import ChatEmptyState from "./components/chat-empty-state";
import ChatInputBar from "./components/chat-input-bar";
import { MessageSquare, Loader2 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ document_id: string; title: string; snippet: string }>;
  tool_calls?: Array<{ id: string; name: string; arguments: Record<string, unknown>; result?: string }>;
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
  const starterPrompts = useMemo(() => [t("starter1"), t("starter2"), t("starter3"), t("starter4"), t("starter5")], [t]);

  useEffect(() => { loadSessions(); }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const loadSessions = async () => {
    try { const res = await api.get("/chat/sessions", { params: { limit: 50 } }); setSessions(res.data.sessions || []); }
    catch (error) { console.error("Failed to load chat sessions:", error); } finally { setSessionsLoading(false); }
  };

  const loadSessionMessages = async (sid: string) => {
    setSessionId(sid); setMessages([]);
    try {
      const res = await api.get(`/chat/sessions/${sid}/messages`, { params: { limit: 100 } });
      const raw = Array.isArray(res.data) ? res.data : res.data.messages || [];
      setMessages(raw.map((m: Record<string, unknown>) => ({
        id: m.id as string, role: m.role as "user" | "assistant", content: m.content as string,
        sources: m.sources as Message["sources"], tool_calls: m.tool_calls as Message["tool_calls"],
      })));
    } catch (error) { console.error("Failed to load session messages:", error); }
  };

  const createNewSession = () => { setSessionId(null); setMessages([]); };

  const deleteSession = async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try { await api.delete(`/chat/sessions/${sid}`); setSessions((p) => p.filter((s) => s.id !== sid)); if (sessionId === sid) createNewSession(); }
    catch (error) { console.error("Failed to delete session:", error); }
  };

  const sendMessage = async (text?: string) => {
    const msg = text || input;
    if (!msg.trim() || loading) return;
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: msg }]);
    setInput(""); setLoading(true);
    try {
      let sid = sessionId;
      if (!sid) { const r = await api.post("/chat/sessions", { title: msg.slice(0, 100) }); sid = r.data.id; setSessionId(sid); loadSessions(); }
      const res = await api.post(`/chat/sessions/${sid}/messages`, { message: msg });
      setMessages((prev) => [...prev, {
        id: res.data.message?.id || crypto.randomUUID(), role: "assistant",
        content: res.data.message?.content || res.data.assistant_message || t("noResponse"),
        sources: res.data.message?.sources, tool_calls: res.data.message?.tool_calls,
      }]);
      loadSessions();
    } catch {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "assistant", content: t("errorResponse") }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="flex h-full">
      {sidebarOpen && (
        <SessionSidebar sessions={sessions} sessionId={sessionId} onSelect={loadSessionMessages}
          onDelete={deleteSession} onNew={createNewSession} loading={sessionsLoading} t={t} />
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="p-2 border-b flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <MessageSquare className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium text-muted-foreground">{sessionId ? t("conversation") : t("newChat")}</span>
        </div>
        <CardContent className="flex-1 overflow-auto p-4 space-y-4 min-h-0">
          {messages.length === 0 && <ChatEmptyState starterPrompts={starterPrompts} onSend={sendMessage} t={t} />}
          {messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-4 py-2 text-sm flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-brand-teal" />{t("thinking")}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </CardContent>
        <ChatInputBar input={input} onInputChange={setInput} onSubmit={() => sendMessage()} loading={loading} t={t} />
      </div>
    </div>
  );
}
