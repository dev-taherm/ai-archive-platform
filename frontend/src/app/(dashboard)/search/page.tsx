"use client";

import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  Search as SearchIcon,
  FileText,
  Clock,
  Filter,
  X,
  BookmarkPlus,
  Trash2,
  ChevronLeft,
  ChevronRight,
  History,
  Sparkles,
  Globe,
  Tag,
  Hash,
} from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import type {
  SearchResponse,
  SearchRequest,
  SavedSearch,
  SearchHistoryEntry,
} from "@/types/api";

function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const words = query.trim().split(/\s+/).filter(Boolean);
  const escapedWords = words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escapedWords.join("|")})`, "gi");
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-yellow-200 text-foreground dark:bg-yellow-800 dark:text-foreground rounded px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function FacetsCard({ data }: { data: SearchResponse }) {
  const t = useTranslations("search");
  const facets = useMemo(() => {
    const docTypes: Record<string, number> = {};
    const languages: Record<string, number> = {};
    const matchSources: Record<string, number> = {};
    data.results.forEach((r) => {
      if (r.doc_type) docTypes[r.doc_type] = (docTypes[r.doc_type] || 0) + 1;
      if (r.language) languages[r.language] = (languages[r.language] || 0) + 1;
      if (r.match_source) matchSources[r.match_source] = (matchSources[r.match_source] || 0) + 1;
    });
    return { docTypes, languages, matchSources };
  }, [data]);

  const hasFacets =
    Object.keys(facets.docTypes).length > 0 ||
    Object.keys(facets.languages).length > 0 ||
    Object.keys(facets.matchSources).length > 0;

  if (!hasFacets) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Filter className="h-4 w-4" />
          {t("resultFacets")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.keys(facets.matchSources).length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <Sparkles className="h-3 w-3" /> {t("matchSource")}
            </p>
            <div className="space-y-1">
              {Object.entries(facets.matchSources)
                .sort((a, b) => b[1] - a[1])
                .map(([source, count]) => (
                  <div key={source} className="flex items-center justify-between text-sm">
                    <Badge variant="outline" className="text-xs">{source}</Badge>
                    <span className="text-muted-foreground">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
        {Object.keys(facets.docTypes).length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <FileText className="h-3 w-3" /> {t("documentType")}
            </p>
            <div className="space-y-1">
              {Object.entries(facets.docTypes)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm">
                    <span className="capitalize">{type}</span>
                    <span className="text-muted-foreground">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
        {Object.keys(facets.languages).length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <Globe className="h-3 w-3" /> {t("language")}
            </p>
            <div className="space-y-1">
              {Object.entries(facets.languages)
                .sort((a, b) => b[1] - a[1])
                .map(([lang, count]) => (
                  <div key={lang} className="flex items-center justify-between text-sm">
                    <span>{lang.toUpperCase()}</span>
                    <span className="text-muted-foreground">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function SearchPage() {
  const t = useTranslations("search");
  const tc = useTranslations("common");
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
        <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
        <p className="text-muted-foreground">
          {t("subtitle")}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-teal" />
            <Input
              placeholder={t("searchPlaceholder")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className={showFilters ? "bg-primary/10" : ""}
          >
            <Filter className="mr-2 h-4 w-4" />
            {t("filters")}
          </Button>
          <Button type="submit" disabled={searchMutation.isPending}>
            {searchMutation.isPending ? t("searching") : t("search")}
          </Button>
        </div>

        {showFilters && (
          <Card>
            <CardContent className="pt-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{t("type")}</span>
                {(["hybrid", "semantic", "keyword"] as const).map((type) => (
                  <Badge
                    key={type}
                    variant={searchType === type ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => setSearchType(type)}
                  >
                    {type}
                  </Badge>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">{t("docTypes")}</label>
                  <Input
                    placeholder={t("docTypesPlaceholder")}
                    value={filters.doc_types}
                    onChange={(e) => setFilters((f) => ({ ...f, doc_types: e.target.value }))}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">{t("languages")}</label>
                  <Input
                    placeholder={t("languagesPlaceholder")}
                    value={filters.languages}
                    onChange={(e) => setFilters((f) => ({ ...f, languages: e.target.value }))}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">{t("tags")}</label>
                  <Input
                    placeholder={t("tagsPlaceholder")}
                    value={filters.tags}
                    onChange={(e) => setFilters((f) => ({ ...f, tags: e.target.value }))}
                    className="mt-1"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-muted-foreground">{t("from")}</label>
                    <Input
                      type="date"
                      value={filters.date_from}
                      onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">{t("to")}</label>
                    <Input
                      type="date"
                      value={filters.date_to}
                      onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
                      className="mt-1"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </form>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-4">
          {searchMutation.data && (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>
                    {t("resultsSummary", { count: searchMutation.data.total_count, query: lastQuery, time: searchMutation.data.search_time_ms.toFixed(0) })}
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
                    <p className="text-sm text-muted-foreground">
                      {t("noResultsDesc")}
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {searchMutation.data.results.map((result, i) => (
                    <Link
                      key={`${result.document_id}-${i}`}
                      href={`/documents/${result.document_id}`}
                    >
                      <Card className="cursor-pointer transition-colors hover:bg-muted/50">
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2 text-base">
                              <FileText className="h-4 w-4 text-brand-teal" />
                              <HighlightedText text={result.title || t("untitled")} query={lastQuery} />
                            </CardTitle>
                            <div className="flex items-center gap-2 shrink-0">
                              <Badge variant="outline" className="text-xs">
                                {result.match_source}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {(result.score * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground line-clamp-3">
                            <HighlightedText text={result.snippet} query={lastQuery} />
                          </p>
                          {result.highlights && result.highlights.length > 0 && (
                            <div className="mt-2 space-y-1">
                              {result.highlights.slice(0, 2).map((h, hi) => (
                                <p key={hi} className="text-xs text-muted-foreground italic">
                                  &hellip;<HighlightedText text={h} query={lastQuery} />&hellip;
                                </p>
                              ))}
                            </div>
                          )}
                          <div className="mt-2 flex gap-2">
                            {result.doc_type && (
                              <Badge variant="secondary" className="text-xs">
                                {result.doc_type}
                              </Badge>
                            )}
                            {result.language && (
                              <Badge variant="secondary" className="text-xs">
                                {result.language}
                              </Badge>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    </Link>
                  ))}
                </div>
              )}

              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <span className="text-sm text-muted-foreground">
                    {t("pageInfo", { current: currentPage, total: totalPages })}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(offset - maxResults)}
                      disabled={offset === 0}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      {tc("previous")}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(offset + maxResults)}
                      disabled={currentPage >= totalPages}
                    >
                      {tc("next")}
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}

          {searchMutation.isError && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <p className="text-sm text-destructive">
                  {t("searchFailed")}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          {searchMutation.data && searchMutation.data.results.length > 0 && (
            <FacetsCard data={searchMutation.data} />
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
                    onClick={() => {
                      setQuery(entry.query);
                      setLastQuery(entry.query);
                      setSearchType(entry.search_type as SearchRequest["search_type"]);
                      setOffset(0);
                      searchMutation.mutate(entry.query);
                    }}
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
                  <div key={saved.id} className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-muted">
                    <button
                      className="flex-1 text-left"
                      onClick={() => {
                        setQuery(saved.query);
                        setLastQuery(saved.query);
                        setSearchType(saved.search_type as SearchRequest["search_type"]);
                        setOffset(0);
                        searchMutation.mutate(saved.query);
                      }}
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
                      onClick={() => deleteMutation.mutate(saved.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
