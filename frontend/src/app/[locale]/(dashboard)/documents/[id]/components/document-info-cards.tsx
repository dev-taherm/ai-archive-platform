"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Calendar, Lightbulb } from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import type { Document } from "@/types/api";
import type { TranslationFunction } from "./types";

interface DocumentInfoCardsProps {
  document: Document;
  t: TranslationFunction;
}

export default function DocumentInfoCards({ document: doc, t }: DocumentInfoCardsProps) {
  return (
    <>
      <div className="grid gap-6 md:grid-cols-2">
        {/* Classification */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("classification")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("type")}</span>
              <span className="font-medium">{doc.doc_type}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("confidence")}</span>
              <span className="font-medium">
                {doc.classification_confidence != null
                  ? `${(doc.classification_confidence * 100).toFixed(1)}%`
                  : "—"}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("pages")}</span>
              <span className="font-medium">{doc.page_count || "—"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Timestamps */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("timeline")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-brand-teal" />
              <span className="text-muted-foreground">{t("created")}</span>
              <span>{formatDateTime(doc.created_at)}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-brand-teal" />
              <span className="text-muted-foreground">{t("updated")}</span>
              <span>{formatDateTime(doc.updated_at)}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Document Summary */}
      {doc.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4 text-brand-teal" />
              {t("summary")}
            </CardTitle>
            <CardDescription>{t("summaryDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {doc.summary}
            </p>
          </CardContent>
        </Card>
      )}
    </>
  );
}
