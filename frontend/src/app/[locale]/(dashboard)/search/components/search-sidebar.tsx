"use client";

import { useTranslations } from "next-intl";
import { History, BookmarkPlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  SearchResponse,
  SearchRequest,
  SavedSearch,
  SearchHistoryEntry,
} from "@/types/api";
import { FacetsCard } from "./facets-card";

interface SearchSidebarProps {
  searchResponse: SearchResponse | undefined;
  savedSearches: SavedSearch[] | undefined;
  history: SearchHistoryEntry[] | undefined;
  onLoadHistory: (entry: SearchHistoryEntry) => void;
  onLoadSaved: (saved: SavedSearch) => void;
  onDeleteSaved: (id: string) => void;
}

export function SearchSidebar({
  searchResponse,
  savedSearches,
  history,
  onLoadHistory,
  onLoadSaved,
  onDeleteSaved,
}: SearchSidebarProps) {
  const t = useTranslations("search");

  return (
    <div className="space-y-4">
      {searchResponse && searchResponse.results.length > 0 && (
        <FacetsCard data={searchResponse} />
      )}

      {history && history.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <History className="h-4 w-4" />
              {t("recentSearches")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {history.map((entry) => (
              <button
                key={entry.id}
                className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                onClick={() => onLoadHistory(entry)}
              >
                <span className="truncate">{entry.query}</span>
                <Badge variant="outline" className="ml-2 text-xs shrink-0">
                  {entry.result_count}
                </Badge>
              </button>
            ))}
          </CardContent>
        </Card>
      )}

      {savedSearches && savedSearches.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <BookmarkPlus className="h-4 w-4" />
              {t("savedSearches")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {savedSearches.map((saved) => (
              <div
                key={saved.id}
                className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-muted"
              >
                <button
                  className="flex-1 text-left"
                  onClick={() => onLoadSaved(saved)}
                >
                  <span className="text-sm font-medium">{saved.name}</span>
                  <span className="block text-xs text-muted-foreground truncate">
                    {saved.query}
                  </span>
                </button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0"
                  onClick={() => onDeleteSaved(saved.id)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
