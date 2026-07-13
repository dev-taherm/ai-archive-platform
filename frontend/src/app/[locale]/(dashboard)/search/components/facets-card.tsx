"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  FileText,
  Filter,
  Globe,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { SearchResponse } from "@/types/api";

interface FacetsCardProps {
  data: SearchResponse;
}

export function FacetsCard({ data }: FacetsCardProps) {
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
