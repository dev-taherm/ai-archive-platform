"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Search as SearchIcon,
  Clock,
  X,
  BookmarkPlus,
} from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import type {
  SearchResponse,
  SearchRequest,
  SavedSearch,
  SearchHistoryEntry,
} from "@/types/api";
import { SearchForm } from "./components/search-form";
import { SearchResultCard } from "./components/search-result-card";
import { SearchPagination } from "./components/search-pagination";
import { SearchSidebar } from "./components/search-sidebar";

export default function SearchPage() {
  const t = useTranslations("search");
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [searchType, setSearchType] = useState<SearchRequest["search_type"]>("hybrid");
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState({
    doc_types: "",
    languages: "",
    tags: "",
    date_from: "",
    date_to: "",
  });
  const [saveName, setSaveName] = useState("");
  const [showSave, setShowSave] = useState(false);
  const maxResults = 20;
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const searchMutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const request: SearchRequest = {
        query: searchQuery,
        search_type: searchType,
        max_results: maxResults,
        offset,
      };

      const activeFilters: Record<string, unknown> = {};
      if (filters.doc_types) activeFilters.doc_types = filters.doc_types.split(",").map((s) => s.trim());
      if (filters.languages) activeFilters.languages = filters.languages.split(",").map((s) => s.trim());
      if (filters.tags) activeFilters.tags = filters.tags.split(",").map((s) => s.trim());
      if (filters.date_from) activeFilters.date_from = filters.date_from;
      if (filters.date_to) activeFilters.date_to = filters.date_to;
      if (Object.keys(activeFilters).length > 0) request.filters = activeFilters;

      const response = await api.post<SearchResponse>("/search/search", request);
      return response.data;
    },
  });

  const { data: savedSearches } = useQuery<SavedSearch[]>({
    queryKey: ["search", "saved"],
    queryFn: async () => {
      const res = await api.get("/search/saved");
      return res.data;
    },
  });

  const { data: history } = useQuery<SearchHistoryEntry[]>({
    queryKey: ["search", "history"],
    queryFn: async () => {
      const res = await api.get("/search/history", { params: { limit: 10 } });
      return res.data;
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/search/saved", {
        name: saveName,
        query: lastQuery,
        search_type: searchType,
        filters: filters.doc_types || filters.languages || filters.tags
          ? {
              ...(filters.doc_types && { doc_types: filters.doc_types.split(",").map((s) => s.trim()) }),
              ...(filters.languages && { languages: filters.languages.split(",").map((s) => s.trim()) }),
              ...(filters.tags && { tags: filters.tags.split(",").map((s) => s.trim()) }),
            }
          : {},
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["search", "saved"] });
      setSaveName("");
      setShowSave(false);
      toast({ title: t("save") });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete("/search/saved", { data: { id } });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["search", "saved"] });
      toast({ title: t("save") });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLastQuery(query);
    setOffset(0);
    searchMutation.mutate(query);
  };

  const handlePageChange = (newOffset: number) => {
    setOffset(newOffset);
    if (lastQuery) searchMutation.mutate(lastQuery);
  };

  const totalPages = searchMutation.data
    ? Math.ceil(searchMutation.data.total_count / maxResults)
    : 0;
  const currentPage = Math.floor(offset / maxResults) + 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">
          {t("title")}
        </h1>
        <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      <SearchForm
        query={query}
        onQueryChange={setQuery}
        searchType={searchType}
        onSearchTypeChange={setSearchType}
        showFilters={showFilters}
        onToggleFilters={() => setShowFilters((v) => !v)}
        filters={filters}
        onFiltersChange={setFilters}
        onSubmit={handleSubmit}
        searching={searchMutation.isPending}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-4">
          {searchMutation.data && (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>
                    {t("resultsSummary", {
                      count: searchMutation.data.total_count,
                      query: lastQuery,
                      time: searchMutation.data.search_time_ms.toFixed(0),
                    })}
                  </span>
                  <Badge variant="outline" className="ml-2">
                    {searchMutation.data.search_type}
                  </Badge>
                </div>
                {lastQuery && (
                  <div className="flex items-center gap-2">
                    {showSave ? (
                      <div className="flex items-center gap-2">
                        <Input
                          placeholder={t("saveSearchPlaceholder")}
                          value={saveName}
                          onChange={(e) => setSaveName(e.target.value)}
                          className="h-8 w-40 text-sm"
                        />
                        <Button
                          size="sm"
                          onClick={() => saveMutation.mutate()}
                          disabled={!saveName.trim() || saveMutation.isPending}
                        >
                          {t("save")}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setShowSave(false)}>
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => setShowSave(true)}>
                        <BookmarkPlus className="mr-2 h-4 w-4" />
                        {t("saveSearch")}
                      </Button>
                    )}
                  </div>
                )}
              </div>

              {searchMutation.data.results.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <SearchIcon className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
                    <p className="text-lg font-medium">{t("noResults")}</p>
                    <p className="text-sm text-muted-foreground">{t("noResultsDesc")}</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {searchMutation.data.results.map((result, i) => (
                    <SearchResultCard
                      key={`${result.document_id}-${i}`}
                      result={result}
                      index={i}
                      query={lastQuery}
                    />
                  ))}
                </div>
              )}

              {totalPages > 1 && (
                <SearchPagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  offset={offset}
                  maxResults={maxResults}
                  onPageChange={handlePageChange}
                />
              )}
            </>
          )}

          {searchMutation.isError && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <p className="text-sm text-destructive">{t("searchFailed")}</p>
              </CardContent>
            </Card>
          )}
        </div>

        <SearchSidebar
          searchResponse={searchMutation.data}
          savedSearches={savedSearches}
          history={history}
          onLoadHistory={(entry) => {
            setQuery(entry.query);
            setLastQuery(entry.query);
            setSearchType(entry.search_type as SearchRequest["search_type"]);
            setOffset(0);
            searchMutation.mutate(entry.query);
          }}
          onLoadSaved={(saved) => {
            setQuery(saved.query);
            setLastQuery(saved.query);
            setSearchType(saved.search_type as SearchRequest["search_type"]);
            setOffset(0);
            searchMutation.mutate(saved.query);
          }}
          onDeleteSaved={(id) => deleteMutation.mutate(id)}
        />
      </div>
    </div>
  );
}
