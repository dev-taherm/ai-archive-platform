"use client";

import Link from "next/link";
import { Lightbulb, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatDateTime } from "@/lib/utils";
import type { Document } from "@/types/api";

interface SummariesTabProps {
  summaries: Document[];
  t: Function;
}

export default function SummariesTab({ summaries, t }: SummariesTabProps) {
  return (
    <div className="space-y-4">
      {summaries.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Lightbulb className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
            <p className="text-lg font-medium">{t("noSummaries")}</p>
            <p className="text-sm text-muted-foreground">{t("noSummariesDesc")}</p>
          </CardContent>
        </Card>
      ) : (
        summaries.map((doc) => (
          <Card key={doc.id} className="overflow-hidden">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-base">
                    <Link href={`/documents/${doc.id}`} className="hover:underline">{doc.title || doc.file_name}</Link>
                  </CardTitle>
                  <CardDescription className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">{doc.doc_type}</Badge>
                    <span>{doc.language}</span>
                    <span>&middot;</span>
                    <span>{doc.word_count.toLocaleString()} words</span>
                  </CardDescription>
                </div>
                <Link href={`/documents/${doc.id}`}>
                  <Button variant="ghost" size="sm"><Eye className="mr-1 h-3 w-3" /> {t("view")}</Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-muted-foreground line-clamp-3">{doc.summary}</p>
              <p className="mt-2 text-xs text-muted-foreground">{formatDateTime(doc.updated_at)}</p>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}
