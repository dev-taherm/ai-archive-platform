"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { Search as SearchIcon, FileText, Clock, Filter, X } from "lucide-react";
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
import type { SearchResponse, SearchRequest } from "@/types/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [searchType, setSearchType] = useState<SearchRequest["search_type"]>("hybrid");
  const [filters, setFilters] = useState({
    doc_types: "",
    languages: "",
    tags: "",
  });

  const searchMutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const request: SearchRequest = {
        query: searchQuery,
        search_type: searchType,
        max_results: 20,
      };

      if (filters.doc_types || filters.languages || filters.tags) {
        request.filters = {};
        if (filters.doc_types) request.filters.doc_types = filters.doc_types.split(",").map((s) => s.trim());
        if (filters.languages) request.filters.languages = filters.languages.split(",").map((s) => s.trim());
        if (filters.tags) request.filters.tags = filters.tags.split(",").map((s) => s.trim());
      }

      const response = await api.post<SearchResponse>("/search/search", request);
      return response.data;
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLastQuery(query);
    searchMutation.mutate(query);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Search</h1>
        <p className="text-muted-foreground">
          Search through your archived documents
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search documents..."
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
            Filters
          </Button>
          <Button type="submit" disabled={searchMutation.isPending}>
            {searchMutation.isPending ? "Searching..." : "Search"}
          </Button>
        </div>

        {showFilters && (
          <Card>
            <CardContent className="pt-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Type:</span>
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
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">Doc Types (comma separated)</label>
                  <Input
                    placeholder="pdf, text, code..."
                    value={filters.doc_types}
                    onChange={(e) => setFilters((f) => ({ ...f, doc_types: e.target.value }))}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Languages</label>
                  <Input
                    placeholder="en, ar..."
                    value={filters.languages}
                    onChange={(e) => setFilters((f) => ({ ...f, languages: e.target.value }))}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Tags</label>
                  <Input
                    placeholder="important, draft..."
                    value={filters.tags}
                    onChange={(e) => setFilters((f) => ({ ...f, tags: e.target.value }))}
                    className="mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </form>

      {searchMutation.data && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>
              Found {searchMutation.data.total_count} results for &quot;{lastQuery}&quot; in{" "}
              {searchMutation.data.search_time_ms.toFixed(0)}ms
            </span>
            <Badge variant="outline" className="ml-2">
              {searchMutation.data.search_type}
            </Badge>
          </div>

          {searchMutation.data.results.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <SearchIcon className="mb-4 h-12 w-12 text-muted-foreground" />
                <p className="text-lg font-medium">No results found</p>
                <p className="text-sm text-muted-foreground">
                  Try different keywords or adjust your filters
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
                          <FileText className="h-4 w-4" />
                          {result.title}
                        </CardTitle>
                        <div className="flex items-center gap-2">
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
                        {result.snippet}
                      </p>
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
        </div>
      )}

      {searchMutation.isError && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-sm text-destructive">
              Search failed. Please try again.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
