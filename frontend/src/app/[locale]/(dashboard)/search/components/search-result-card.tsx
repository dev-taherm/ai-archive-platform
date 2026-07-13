"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { HighlightedText } from "./highlighted-text";

interface SearchResultItem {
  document_id: string;
  title?: string;
  snippet: string;
  score: number;
  match_source?: string;
  doc_type?: string;
  language?: string;
  highlights?: string[];
}

interface SearchResultCardProps {
  result: SearchResultItem;
  index: number;
  query: string;
}

export function SearchResultCard({ result, index, query }: SearchResultCardProps) {
  const t = useTranslations("search");

  return (
    <Link href={`/documents/${result.document_id}`}>
      <Card className="cursor-pointer transition-colors hover:bg-muted/50">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-brand-teal" />
              <HighlightedText text={result.title || t("untitled")} query={query} />
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
            <HighlightedText text={result.snippet} query={query} />
          </p>
          {result.highlights && result.highlights.length > 0 && (
            <div className="mt-2 space-y-1">
              {result.highlights.slice(0, 2).map((h, hi) => (
                <p key={hi} className="text-xs text-muted-foreground italic">
                  &hellip;<HighlightedText text={h} query={query} />&hellip;
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
  );
}
