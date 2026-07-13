"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain } from "lucide-react";
import { entityTypeVariant } from "@/lib/constants";
import type { DocumentEntity } from "@/types/api";
import type { TranslationFunction } from "./types";

interface EntityListProps {
  entities: DocumentEntity[];
  t: TranslationFunction;
}

export default function EntityList({ entities, t }: EntityListProps) {
  if (!entities || entities.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain className="h-4 w-4 text-brand-cyan" />
          {t("extractedEntities")}
        </CardTitle>
        <CardDescription>{t("entitiesDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {entities.map((entity, index) => (
            <div
              key={`${entity.name}-${entity.type}-${index}`}
              className="flex items-start gap-3 rounded-md border p-3"
            >
              <Badge
                variant={entityTypeVariant[entity.type] || "outline"}
                className="mt-0.5 shrink-0"
              >
                {entity.type}
              </Badge>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{entity.name}</p>
                {entity.context && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {entity.context}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
