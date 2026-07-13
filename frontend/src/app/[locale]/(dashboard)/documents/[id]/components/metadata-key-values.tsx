"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Info } from "lucide-react";
import type { DocumentMetadata } from "@/types/api";
import type { TranslationFunction } from "./types";

interface MetadataKeyValuesProps {
  metadata: DocumentMetadata;
  t: TranslationFunction;
}

export default function MetadataKeyValues({ metadata, t }: MetadataKeyValuesProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Info className="h-4 w-4 text-brand-cyan" />
          {t("documentMetadata")}
        </CardTitle>
        <CardDescription>{t("metadataDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {metadata.title && (
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("titleLabel")}</span>
              <span className="font-medium">{metadata.title}</span>
            </div>
          )}
          {metadata.author && (
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("author")}</span>
              <span className="font-medium">{metadata.author}</span>
            </div>
          )}
          {metadata.subject && (
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("subject")}</span>
              <span className="font-medium">{metadata.subject}</span>
            </div>
          )}
          {metadata.creation_date && (
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("creationDate")}</span>
              <span className="font-medium">{metadata.creation_date}</span>
            </div>
          )}
          {metadata.modification_date && (
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("modificationDate")}</span>
              <span className="font-medium">{metadata.modification_date}</span>
            </div>
          )}
          {metadata.char_count > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("characters")}</span>
              <span className="font-medium">{metadata.char_count.toLocaleString()}</span>
            </div>
          )}
          {Object.keys(metadata.extra).length > 0 && (
            <>
              <div className="my-2 border-t" />
              <p className="text-sm font-medium text-muted-foreground">{t("additionalMetadata")}</p>
              {Object.entries(metadata.extra).map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{key}</span>
                  <span className="font-medium">
                    {typeof value === "object" ? JSON.stringify(value) : String(value)}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
