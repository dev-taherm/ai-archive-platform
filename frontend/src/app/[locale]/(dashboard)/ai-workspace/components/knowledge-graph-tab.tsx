"use client";

import { Network } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface GraphNode {
  id: string;
  name: string;
  type: string;
  count: number;
  x: number;
  y: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

interface KnowledgeGraphTabProps {
  graphData: { nodes: GraphNode[]; edges: GraphEdge[] };
  typeColors: Record<string, string>;
  t: Function;
}

export default function KnowledgeGraphTab({
  graphData,
  typeColors,
  t,
}: KnowledgeGraphTabProps) {
  return (
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
                    const tgt = graphData.nodes.find((n) => n.id === edge.target);
                    if (!s || !tgt) return null;
                    return (
                      <line key={`edge-${i}`} x1={s.x} y1={s.y} x2={tgt.x} y2={tgt.y}
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
  );
}
