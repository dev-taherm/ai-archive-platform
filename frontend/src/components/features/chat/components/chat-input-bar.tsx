"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send } from "lucide-react";

interface ChatInputBarProps {
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  t: Function;
}

export default function ChatInputBar({
  input,
  onInputChange,
  onSubmit,
  loading,
  t,
}: ChatInputBarProps) {
  return (
    <div className="p-4 border-t">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="flex gap-2"
      >
        <Input
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder={t("inputPlaceholder")}
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
