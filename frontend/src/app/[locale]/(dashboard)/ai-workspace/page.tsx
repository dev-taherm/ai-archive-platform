"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { RefreshCw, Brain, Lightbulb, BarChart3, Users, Copy, Network } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Document, DashboardStats, EntityAgg } from "@/types/api";
import WorkspaceStats from "./components/workspace-stats";
import SummariesTab from "./components/summaries-tab";
import ClassificationsTab from "./components/classifications-tab";
import EntitiesTab from "./components/entities-tab";
import DuplicatesTab from "./components/duplicates-tab";
import KnowledgeGraphTab from "./components/knowledge-graph-tab";

type Tab = "summaries" | "classifications" | "entities" | "duplicates" | "graph";

export default function AIWorkspacePage() {
  const t = useTranslations("aiWorkspace");
  const tc = useTranslations("common");
  const [activeTab, setActiveTab] = useState<Tab>("summaries");
  const [search, setSearch] = useState("");

  const tabs: { id: Tab; label: string; icon: typeof Brain }[] = useMemo(() => [
    { id: "summaries", label: t("summaries"), icon: Lightbulb },
    { id: "classifications", label: t("classifications"), icon: BarChart3 },
    { id: "entities", label: t("entities"), icon: Users },
    { id: "duplicates", label: t("duplicates"), icon: Copy },
    { id: "graph", label: t("knowledgeGraph"), icon: Network },
  ], [t]);

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
    queryFn: async () => { const res = await api.get("/dashboard/stats"); return res.data; },
  });

  const docsWithSummaries = useMemo(
    () => documents.filter((d) => d.summary && d.processing_status === "completed"), [documents]);

  const docsWithEntities = useMemo(
    () => documents.filter((d) => d.entities && d.entities.length > 0 && d.processing_status === "completed"), [documents]);

  const classificationGroups = useMemo(() => {
    const groups: Record<string, { count: number; docs: Document[] }> = {};
    documents.forEach((d) => {
      if (d.processing_status !== "completed") return;
      const type = d.doc_type || "unknown";
      if (!groups[type]) groups[type] = { count: 0, docs: [] };
      groups[type].count++; groups[type].docs.push(d);
    });
    return Object.entries(groups).sort((a, b) => b[1].count - a[1].count);
  }, [documents]);

  const aggregatedEntities = useMemo(() => {
    const map = new Map<string, EntityAgg>();
    docsWithEntities.forEach((doc) => {
      doc.entities!.forEach((entity) => {
        const key = `${entity.name}::${entity.type}`;
        if (!map.has(key)) map.set(key, { name: entity.name, type: entity.type, count: 0, documents: [] });
        const agg = map.get(key)!; agg.count++;
        agg.documents.push({ id: doc.id, title: doc.title || doc.file_name });
      });
    });
    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [docsWithEntities]);

  const filteredSummaries = useMemo(() => {
    if (!search) return docsWithSummaries;
    const q = search.toLowerCase();
    return docsWithSummaries.filter(
      (d) => (d.title || d.file_name).toLowerCase().includes(q) || d.summary!.toLowerCase().includes(q));
  }, [docsWithSummaries, search]);

  const filteredEntities = useMemo(() => {
    if (!search) return aggregatedEntities;
    const q = search.toLowerCase();
    return aggregatedEntities.filter((e) => e.name.toLowerCase().includes(q) || e.type.toLowerCase().includes(q));
  }, [aggregatedEntities, search]);

  const graphData = useMemo(() => {
    const nodes: { id: string; name: string; type: string; count: number; x: number; y: number }[] = [];
    const edges: { source: string; target: string; weight: number }[] = [];
    const nodeMap = new Map<string, number>();
    const edgeMap = new Map<string, number>();
    aggregatedEntities.slice(0, 30).forEach((e, i) => {
      const id = `${e.name}::${e.type}`; nodeMap.set(id, i);
      const angle = (2 * Math.PI * i) / 30; const radius = 180;
      nodes.push({ id, name: e.name, type: e.type, count: e.count, x: 250 + radius * Math.cos(angle), y: 250 + radius * Math.sin(angle) });
    });
    docsWithEntities.forEach((doc) => {
      if (!doc.entities) return;
      const ids = doc.entities.map((e) => `${e.name}::${e.type}`).filter((id) => nodeMap.has(id));
      for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) {
        const key = [ids[i], ids[j]].sort().join("|||");
        edgeMap.set(key, (edgeMap.get(key) || 0) + 1);
      }
    });
    edgeMap.forEach((weight, key) => {
      const [s, tgt] = key.split("|||");
      if (weight >= 2) edges.push({ source: s, target: tgt, weight });
    });
    return { nodes, edges };
  }, [aggregatedEntities, docsWithEntities]);

  const typeColors: Record<string, string> = {
    PERSON: "#0F8B8D", ORGANIZATION: "#38BDF8", LOCATION: "#0B1F3A",
    DATE: "#6b7280", EVENT: "#f59e0b", MONEY: "#ef4444",
  };

  const completedCount = documents.filter((d) => d.processing_status === "completed").length;

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

      <WorkspaceStats docCount={completedCount} summaryCount={docsWithSummaries.length} entityCount={aggregatedEntities.length} typeCount={classificationGroups.length} t={t} />

      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => { setActiveTab(tab.id); setSearch(""); }}
              className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${activeTab === tab.id ? "bg-brand-teal/10 text-brand-teal shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>
              <Icon className="h-4 w-4" /> {tab.label}
            </button>
          );
        })}
      </div>

      {(activeTab === "summaries" || activeTab === "entities") && (
        <div className="relative max-w-sm">
          <Input placeholder={activeTab === "summaries" ? t("searchSummaries") : t("searchEntities")} value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12 text-muted-foreground">{t("loading")}</div>
      ) : (
        <>
          {activeTab === "summaries" && <SummariesTab summaries={filteredSummaries} t={t} />}
          {activeTab === "classifications" && <ClassificationsTab groups={classificationGroups} totalDocCount={documents.length} t={t} />}
          {activeTab === "entities" && <EntitiesTab entities={filteredEntities} typeColors={typeColors} search={search} t={t} tc={tc} />}
          {activeTab === "duplicates" && <DuplicatesTab stats={stats} t={t} tc={tc} />}
          {activeTab === "graph" && <KnowledgeGraphTab graphData={graphData} typeColors={typeColors} t={t} />}
        </>
      )}
    </div>
  );
}
