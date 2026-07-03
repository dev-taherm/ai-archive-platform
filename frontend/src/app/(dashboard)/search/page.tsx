"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search as SearchIcon, FileText, Clock } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { SearchResponse } from "@/types/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");

  const searchMutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const response = await api.post<SearchResponse>("/search", {
        query: searchQuery,
        page_size: 20,
      });
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
        <h1 className="text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">
          Search through your archived documents
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button type="submit" disabled={searchMutation.isPending}>
          {searchMutation.isPending ? "Searching..." : "Search"}
        </Button>
      </form>

      {searchMutation.data && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>
              Found {searchMutation.data.total} results for &quot;{lastQuery}&quot; in{" "}
              {searchMutation.data.took_ms}ms
            </span>
          </div>

          {searchMutation.data.results.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <SearchIcon className="mb-4 h-12 w-12 text-muted-foreground" />
                <p className="text-lg font-medium">No results found</p>
                <p className="text-sm text-muted-foreground">
                  Try different keywords or check your filters
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {searchMutation.data.results.map((result) => (
                <Card key={result.chunk_id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <FileText className="h-4 w-4" />
                        {result.document_title}
                      </CardTitle>
                      <span className="text-xs text-muted-foreground">
                        Score: {(result.score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {result.content}
                    </p>
                    {result.highlights.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {result.highlights.map((highlight, i) => (
                          <p
                            key={i}
                            className="text-xs"
                            dangerouslySetInnerHTML={{ __html: highlight }}
                          />
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
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
