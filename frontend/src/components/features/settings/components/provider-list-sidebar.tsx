"use client";

import { Plus, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ProviderConfig } from "@/types/api";

interface ProviderListSidebarProps {
  providers: ProviderConfig[];
  selectedId: string | null;
  isCreating: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  t: Function;
}

export default function ProviderListSidebar({
  providers,
  selectedId,
  isCreating,
  onSelect,
  onNew,
  t,
}: ProviderListSidebarProps) {
  return (
    <Card className="md:row-span-2">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t("providers")}</CardTitle>
          <Button size="sm" variant="outline" onClick={onNew}>
            <Plus className="h-3.5 w-3.5 me-1" />
            {t("new")}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-2">
        {providers.length === 0 && !isCreating ? (
          <div className="p-4 text-sm text-muted-foreground text-center">
            {t("noProviders")}
          </div>
        ) : (
          <div className="space-y-1">
            {providers.map((p) => (
              <button
                key={p.id}
                onClick={() => onSelect(p.id)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center gap-2 ${
                  selectedId === p.id && !isCreating
                    ? "bg-brand-teal/10 text-brand-teal border border-brand-teal/20"
                    : "hover:bg-muted border border-transparent"
                }`}
              >
                {p.is_default && (
                  <Star className="h-3.5 w-3.5 text-yellow-500 shrink-0 fill-yellow-500" />
                )}
                <span className="truncate flex-1">{p.name}</span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {t(p.provider_type === "google" ? "googleGemini" : p.provider_type)}
                </span>
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
