"use client";

import Link from "next/link";
import { FileText, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { entityTypeVariant } from "@/lib/constants";
import type { EntityAgg } from "@/types/api";

interface EntitiesTabProps {
  entities: EntityAgg[];
  typeColors: Record<string, string>;
  search: string;
  t: Function;
  tc: Function;
}

export default function EntitiesTab({
  entities,
  typeColors: _typeColors,
  search,
  t,
  tc,
}: EntitiesTabProps) {
  return (
    <div className="space-y-4">
      {entities.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Users className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
            <p className="text-lg font-medium">{t("noEntities")}</p>
            <p className="text-sm text-muted-foreground">
              {search ? tc("tryDifferentSearch") : t("noEntitiesDesc")}
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("entityTypes")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {Object.entries(
                  entities.reduce((acc, e) => { acc[e.type] = (acc[e.type] || 0) + 1; return acc; }, {} as Record<string, number>)
                ).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                  <Badge key={type} variant={entityTypeVariant[type] || "outline"}>{type}: {count}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          {entities.map((entity) => (
            <Card key={`${entity.name}::${entity.type}`}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant={entityTypeVariant[entity.type] || "outline"}>{entity.type}</Badge>
                    <CardTitle className="text-base">{entity.name}</CardTitle>
                  </div>
                  <Badge variant="secondary">{t("nDocs", { n: entity.count })}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {entity.documents.slice(0, 5).map((doc) => (
                    <Link key={doc.id} href={`/documents/${doc.id}`} className="flex items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-muted">
                      <FileText className="h-3 w-3 text-brand-teal" /> {doc.title}
                    </Link>
                  ))}
                  {entity.documents.length > 5 && (
                    <p className="text-xs text-muted-foreground pl-2">{t("moreDocuments", { n: entity.documents.length - 5 })}</p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </>
      )}
    </div>
  );
}
