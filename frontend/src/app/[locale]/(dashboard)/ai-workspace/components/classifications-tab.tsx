"use client";

import Link from "next/link";
import { FileText, BarChart3, ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Document } from "@/types/api";

interface ClassificationsTabProps {
  groups: [string, { count: number; docs: Document[] }][];
  totalDocCount: number;
  t: Function;
}

export default function ClassificationsTab({
  groups,
  totalDocCount,
  t,
}: ClassificationsTabProps) {
  return (
    <div className="space-y-4">
      {groups.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <BarChart3 className="mb-4 h-12 w-12 text-brand-cyan opacity-50" />
            <p className="text-lg font-medium">{t("noClassifications")}</p>
            <p className="text-sm text-muted-foreground">{t("noClassificationsDesc")}</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("classificationDistribution")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {groups.map(([type, { count }]) => {
                  const pct = totalDocCount > 0 ? (count / totalDocCount) * 100 : 0;
                  return (
                    <div key={type} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium capitalize">{type}</span>
                        <span className="text-muted-foreground">{t("distribution", { count, pct: pct.toFixed(0) })}</span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-brand-teal to-brand-cyan transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {groups.map(([type, { docs }]) => (
            <Card key={type}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base capitalize">{type}</CardTitle>
                  <Badge variant="secondary">{t("nDocs", { n: docs.length })}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {docs.slice(0, 10).map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-brand-teal" />
                        <Link href={`/documents/${doc.id}`} className="text-sm font-medium hover:underline">
                          {doc.title || doc.file_name}
                        </Link>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {doc.classification_confidence != null && (
                          <span>{(doc.classification_confidence * 100).toFixed(0)}%</span>
                        )}
                        <ArrowRight className="h-3 w-3" />
                      </div>
                    </div>
                  ))}
                  {docs.length > 10 && (
                    <p className="text-xs text-muted-foreground text-center pt-2">{t("andMore", { n: docs.length - 10 })}</p>
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
