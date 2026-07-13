"use client";

import type { FunctionComponent } from "react";
import type { Session } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Plus, MessageSquare, Trash2, Loader2 } from "lucide-react";

interface SessionSidebarProps {
  sessions: Session[];
  sessionId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
  onNew: () => void;
  loading: boolean;
  t: Function;
}

export default function SessionSidebar({
  sessions,
  sessionId,
  onSelect,
  onDelete,
  onNew,
  loading,
  t,
}: SessionSidebarProps) {
  return (
    <div className="w-72 border-r bg-card flex flex-col shrink-0">
      <div className="p-3 border-b">
        <Button
          onClick={onNew}
          className="w-full justify-start gap-2"
          variant="outline"
        >
          <Plus className="h-4 w-4" />
          {t("newConversation")}
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {loading ? (
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
              onClick={() => onSelect(session.id)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-left text-sm transition-colors group ${
                sessionId === session.id
                  ? "bg-brand-teal/10 text-brand-teal"
                  : "hover:bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              <span className="truncate flex-1">{session.title}</span>
              <button
                onClick={(e) => onDelete(session.id, e)}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-destructive/20 rounded"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
