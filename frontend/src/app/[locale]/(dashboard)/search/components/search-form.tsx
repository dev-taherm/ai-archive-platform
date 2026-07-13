"use client";

import { useTranslations } from "next-intl";
import { Search as SearchIcon, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import type { SearchRequest } from "@/types/api";

interface SearchFormFilters {
  doc_types: string;
  languages: string;
  tags: string;
  date_from: string;
  date_to: string;
}

interface SearchFormProps {
  query: string;
  onQueryChange: (value: string) => void;
  searchType: SearchRequest["search_type"];
  onSearchTypeChange: (value: SearchRequest["search_type"]) => void;
  showFilters: boolean;
  onToggleFilters: () => void;
  filters: SearchFormFilters;
  onFiltersChange: (updater: (prev: SearchFormFilters) => SearchFormFilters) => void;
  onSubmit: (e: React.FormEvent) => void;
  searching: boolean;
}

export function SearchForm({
  query,
  onQueryChange,
  searchType,
  onSearchTypeChange,
  showFilters,
  onToggleFilters,
  filters,
  onFiltersChange,
  onSubmit,
  searching,
}: SearchFormProps) {
  const t = useTranslations("search");

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="flex gap-3">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-teal" />
          <Input
            placeholder={t("searchPlaceholder")}
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={onToggleFilters}
          className={showFilters ? "bg-primary/10" : ""}
        >
          <Filter className="mr-2 h-4 w-4" />
          {t("filters")}
        </Button>
        <Button type="submit" disabled={searching}>
          {searching ? t("searching") : t("search")}
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
                  onClick={() => onSearchTypeChange(type)}
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
                  onChange={(e) =>
                    onFiltersChange((f) => ({ ...f, doc_types: e.target.value }))
                  }
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">{t("languages")}</label>
                <Input
                  placeholder={t("languagesPlaceholder")}
                  value={filters.languages}
                  onChange={(e) =>
                    onFiltersChange((f) => ({ ...f, languages: e.target.value }))
                  }
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">{t("tags")}</label>
                <Input
                  placeholder={t("tagsPlaceholder")}
                  value={filters.tags}
                  onChange={(e) =>
                    onFiltersChange((f) => ({ ...f, tags: e.target.value }))
                  }
                  className="mt-1"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-muted-foreground">{t("from")}</label>
                  <Input
                    type="date"
                    value={filters.date_from}
                    onChange={(e) =>
                      onFiltersChange((f) => ({ ...f, date_from: e.target.value }))
                    }
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">{t("to")}</label>
                  <Input
                    type="date"
                    value={filters.date_to}
                    onChange={(e) =>
                      onFiltersChange((f) => ({ ...f, date_to: e.target.value }))
                    }
                    className="mt-1"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </form>
  );
}
