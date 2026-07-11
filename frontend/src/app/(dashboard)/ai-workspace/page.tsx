"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  Brain,
  FileText,
  Lightbulb,
  Users,
  Copy,
  Search,
  BarChart3,
  RefreshCw,
  ArrowRight,
  Eye,
  Layers,
  Network,
} from "lucide-react";
import api from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Document, DocumentEntity, DashboardStats } from "@/types/api";

type Tab = "summaries" | "classifications" | "entities" | "duplicates" | "graph";

interface EntityAgg {
  name: string;
  type: string;
  count: number;
  documents: { id: string; title: string }[];
}

const entityTypeVariant: Record<string, "default" | "secondary" | "outline"> = {
  PERSON: "default",
  ORGANIZATION: "secondary",
  DATE: "outline",
  LOCATION: "default",
  EVENT: "secondary",
  MONEY: "outline",
};

export default function AIWorkspacePage() {
  const t = useTranslations("aiWorkspace");
  const tc = useTranslations("common");
  const [activeTab, setActiveTab] = useState<Tab>("summaries");
  const tabs: { id: Tab; label: string; icon: typeof Brain }[] = useMemo(() => [
    { id: "summaries", label: t("summaries"), icon: Lightbulb },
    { id: "classifications", label: t("classifications"), icon: BarChart3 },
    { id: "entities", label: t("entities"), icon: Users },
    { id: "duplicates", label: t("duplicates"), icon: Copy },
    { id: "graph", label: t("knowledgeGraph"), icon: Network },
  ], [t]);
  const [search, setSearch] = useState("");

  const { data: documents = [], isLoading } = useQuery<Document[]>({
    queryKey: ["documents"],
    queryFn: async () => {
      const res = await api.get("/documents");
      const data = res.data;
      return Array.isArray(data) ? data : data.results || [];
    },
  });

  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      const res = await api.get("/dashboard/stats");
      return res.data;
    },
  });

  const docsWithSummaries = useMemo(
    () => documents.filter((d) => d.summary && d.processing_status === "completed"),
    [documents]
  );

  const docsWithEntities = useMemo(
    () => documents.filter((d) => d.entities && d.entities.length > 0 && d.processing_status === "completed"),
    [documents]
  );

  const classificationGroups = useMemo(() => {
    const groups: Record<string, { count: number; docs: Document[] }> = {};
    documents.forEach((d) => {
      if (d.processing_status !== "completed") return;
      const type = d.doc_type || "unknown";
      if (!groups[type]) groups[type] = { count: 0, docs: [] };
      groups[type].count++;
      groups[type].docs.push(d);
    });
    return Object.entries(groups).sort((a, b) => b[1].count - a[1].count);
  }, [documents]);

  const aggregatedEntities = useMemo(() => {
    const map = new Map<string, EntityAgg>();
    docsWithEntities.forEach((doc) => {
      doc.entities!.forEach((entity) => {
        const key = `${entity.name}::${entity.type}`;
        if (!map.has(key)) {
          map.set(key, { name: entity.name, type: entity.type, count: 0, documents: [] });
        }
        const agg = map.get(key)!;
        agg.count++;
        agg.documents.push({ id: doc.id, title: doc.title || doc.file_name });
      });
    });
    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [docsWithEntities]);

  const filteredSummaries = useMemo(() => {
    if (!search) return docsWithSummaries;
    const q = search.toLowerCase();
    return docsWithSummaries.filter(
      (d) => (d.title || d.file_name).toLowerCase().includes(q) || d.summary!.toLowerCase().includes(q)
    );
  }, [docsWithSummaries, search]);

  const filteredEntities = useMemo(() => {
    if (!search) return aggregatedEntities;
    const q = search.toLowerCase();
    return aggregatedEntities.filter(
      (e) => e.name.toLowerCase().includes(q) || e.type.toLowerCase().includes(q)
    );
  }, [aggregatedEntities, search]);

  const graphData = useMemo(() => {
    const nodes: { id: string; name: string; type: string; count: number; x: number; y: number }[] = [];
    const edges: { source: string; target: string; weight: number }[] = [];
    const nodeMap = new Map<string, number>();
    const edgeMap = new Map<string, number>();

    const topEntities = aggregatedEntities.slice(0, 30);
    topEntities.forEach((e, i) => {
      const id = `${e.name}::${e.type}`;
      nodeMap.set(id, i);
      const angle = (2 * Math.PI * i) / topEntities.length;
      const radius = 180;
      nodes.push({
        id, name: e.name, type: e.type, count: e.count,
        x: 250 + radius * Math.cos(angle),
        y: 250 + radius * Math.sin(angle),
      });
    });

    docsWithEntities.forEach((doc) => {
      if (!doc.entities) return;
      const docEntityIds = doc.entities.map((e) => `${e.name}::${e.type}`).filter((id) => nodeMap.has(id));
      for (let i = 0; i < docEntityIds.length; i++) {
        for (let j = i + 1; j < docEntityIds.length; j++) {
          const key = [docEntityIds[i], docEntityIds[j]].sort().join("|||");
          edgeMap.set(key, (edgeMap.get(key) || 0) + 1);
        }
      }
    });

    edgeMap.forEach((weight, key) => {
      const [s, t] = key.split("|||");
      if (weight >= 2) edges.push({ source: s, target: t, weight });
    });

    return { nodes, edges };
  }, [aggregatedEntities, docsWithEntities]);

  const typeColors: Record<string, string> = {
    PERSON: "#0F8B8D", ORGANIZATION: "#38BDF8", LOCATION: "#0B1F3A",
    DATE: "#6b7280", EVENT: "#f59e0b", MONEY: "#ef4444",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Button variant="brand" onClick={() => api.get("/documents")}>
          <RefreshCw className="mr-2 h-4 w-4" /> {t("refresh")}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("documentsAnalyzed")}</CardDescription>
            <CardTitle className="text-2xl">{documents.filter((d) => d.processing_status === "completed").length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("withSummaries")}</CardDescription>
            <CardTitle className="text-2xl text-brand-teal">{docsWithSummaries.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("uniqueEntities")}</CardDescription>
            <CardTitle className="text-2xl text-brand-cyan">{aggregatedEntities.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("classificationTypes")}</CardDescription>
            <CardTitle className="text-2xl text-brand-teal">{classificationGroups.length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setSearch(""); }}
              className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.id ? "bg-brand-teal/10 text-brand-teal shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Search */}
      {(activeTab === "summaries" || activeTab === "entities") && (
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder={activeTab === "summaries" ? t("searchSummaries") : t("searchEntities")} value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
      )}

      {/* Tab Content */}
      {isLoading ? (
        <div className="flex justify-center py-12 text-muted-foreground">{t("loading")}</div>
      ) : (
        <>
          {/* Summaries Tab */}
          {activeTab === "summaries" && (
            <div className="space-y-4">
              {filteredSummaries.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Lightbulb className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
                    <p className="text-lg font-medium">{t("noSummaries")}</p>
                    <p className="text-sm text-muted-foreground">{t("noSummariesDesc")}</p>
                  </CardContent>
                </Card>
              ) : (
                filteredSummaries.map((doc) => (
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
          )}

          {/* Classifications Tab */}
          {activeTab === "classifications" && (
            <div className="space-y-4">
              {classificationGroups.length === 0 ? (
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
                        {classificationGroups.map(([type, { count }]) => {
                          const pct = documents.length > 0 ? (count / documents.length) * 100 : 0;
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

                  {classificationGroups.map(([type, { docs }]) => (
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
          )}

          {/* Entities Tab */}
          {activeTab === "entities" && (
            <div className="space-y-4">
              {filteredEntities.length === 0 ? (
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
                          filteredEntities.reduce((acc, e) => { acc[e.type] = (acc[e.type] || 0) + 1; return acc; }, {} as Record<string, number>)
                        ).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                          <Badge key={type} variant={entityTypeVariant[type] || "outline"}>{type}: {count}</Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {filteredEntities.map((entity) => (
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
          )}

          {/* Duplicates Tab */}
          {activeTab === "duplicates" && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{t("duplicateDetection")}</CardTitle>
                  <CardDescription>{t("duplicateDetectionDesc")}</CardDescription>
                </CardHeader>
                <CardContent>
                  {stats ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-lg border p-4">
                        <p className="text-sm text-muted-foreground">{t("duplicateFiles")}</p>
                        <p className="text-3xl font-bold text-brand-teal">{stats.duplicate_files}</p>
                      </div>
                      <div className="rounded-lg border p-4">
                        <p className="text-sm text-muted-foreground">Duplicate Groups</p>
                        <p className="text-3xl font-bold text-brand-cyan">{stats.duplicate_groups}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">{t("loadingStats")}</p>
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Copy className="mb-4 h-12 w-12 text-brand-cyan opacity-50" />
                  <p className="text-lg font-medium">{t("duplicateGroupDetails")}</p>
                  <p className="text-sm text-muted-foreground text-center max-w-md">
                    {t("duplicateGroupDesc")}
                  </p>
                  <Link href="/dashboard">
                    <Button variant="brand" className="mt-4"><BarChart3 className="mr-2 h-4 w-4" /> {tc("goToDashboard")}</Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Knowledge Graph Tab */}
          {activeTab === "graph" && (
            <div className="space-y-4">
              {graphData.nodes.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Network className="mb-4 h-12 w-12 text-brand-teal opacity-50" />
                    <p className="text-lg font-medium">{t("noEntitiesToVisualize")}</p>
                    <p className="text-sm text-muted-foreground">{t("noEntitiesToVisualizeDesc")}</p>
                  </CardContent>
                </Card>
              ) : (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">{t("entityCoOccurrence")}</CardTitle>
                      <CardDescription>
                        {t("graphDescription")}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-auto rounded-lg border bg-background">
                        <svg viewBox="0 0 500 500" className="w-full h-[500px]">
                          {graphData.edges.map((edge, i) => {
                            const s = graphData.nodes.find((n) => n.id === edge.source);
                            const t = graphData.nodes.find((n) => n.id === edge.target);
                            if (!s || !t) return null;
                            return (
                              <line key={`edge-${i}`} x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                                className="stroke-muted-foreground/20" strokeWidth={Math.min(edge.weight, 5)} />
                            );
                          })}
                          {graphData.nodes.map((node) => {
                            const r = 6 + Math.min(node.count * 2, 14);
                            return (
                              <g key={node.id}>
                                <circle cx={node.x} cy={node.y} r={r} fill={typeColors[node.type] || "#6b7280"} opacity={0.8}
                                  className="hover:opacity-100 transition-opacity cursor-pointer" />
                                <text x={node.x} y={node.y + r + 12} textAnchor="middle"
                                  className="fill-foreground pointer-events-none" style={{ fontSize: "8px" }}>
                                  {node.name.length > 18 ? node.name.slice(0, 16) + "..." : node.name}
                                </text>
                              </g>
                            );
                          })}
                        </svg>
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">{t("legend")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-3">
                        {[
                          { type: "PERSON", color: "#0F8B8D" }, { type: "ORGANIZATION", color: "#38BDF8" },
                          { type: "LOCATION", color: "#0B1F3A" }, { type: "DATE", color: "#6b7280" },
                          { type: "EVENT", color: "#f59e0b" }, { type: "MONEY", color: "#ef4444" },
                        ].map((item) => (
                          <div key={item.type} className="flex items-center gap-1.5">
                            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                            <span className="text-xs text-muted-foreground">{item.type}</span>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        {t("graphSummary", { n: graphData.nodes.length, m: graphData.edges.length })}
                      </p>
                    </CardContent>
                  </Card>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
