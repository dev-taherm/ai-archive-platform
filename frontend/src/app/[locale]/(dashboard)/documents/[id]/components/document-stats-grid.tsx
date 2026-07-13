"use client";

import { Card, CardContent } from "@/components/ui/card";
import { FileText, Globe, Hash, Layers } from "lucide-react";
import type { Document } from "@/types/api";
import type { TranslationFunction } from "./types";

interface DocumentStatsGridProps {
  document: Document;
  t: TranslationFunction;
}

export default function DocumentStatsGrid({ document: doc, t }: DocumentStatsGridProps) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 text-sm">
            <FileText className="h-4 w-4 text-brand-teal" />
            <span className="text-muted-foreground">{t("type")}</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{doc.doc_type}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 text-sm">
            <Globe className="h-4 w-4 text-brand-cyan" />
            <span className="text-muted-foreground">{t("language")}</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{doc.language || t("unknown")}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 text-sm">
            <Hash className="h-4 w-4 text-brand-teal" />
            <span className="text-muted-foreground">{t("words")}</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{doc.word_count.toLocaleString()}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 text-sm">
            <Layers className="h-4 w-4 text-brand-cyan" />
            <span className="text-muted-foreground">{t("chunks")}</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{doc.chunk_count}</p>
        </CardContent>
      </Card>
    </div>
  );
}
