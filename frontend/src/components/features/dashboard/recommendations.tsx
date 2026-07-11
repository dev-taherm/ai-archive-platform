"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertTriangle,
  Lightbulb,
  Zap,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { RecommendationList } from "@/types/api";

const typeConfig = {
  action: { icon: Zap, color: "text-blue-600", bg: "bg-blue-50 dark:bg-blue-950" },
  insight: { icon: Lightbulb, color: "text-brand-teal", bg: "bg-brand-teal/10" },
  warning: { icon: AlertTriangle, color: "text-orange-600", bg: "bg-orange-50 dark:bg-orange-950" },
};

const priorityVariant: Record<string, "destructive" | "warning" | "secondary"> = {
  high: "destructive",
  medium: "warning",
  low: "secondary",
};

export default function Recommendations() {
  const t = useTranslations("dashboard");
  const { data, isLoading, refetch, isFetching } = useQuery<RecommendationList>({
    queryKey: ["dashboard-recommendations"],
    queryFn: async () => {
      const res = await api.get("/dashboard/recommendations");
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("recommendations")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-4 text-center">
            {t("loadingRecommendations")}
          </p>
        </CardContent>
      </Card>
    );
  }

  const recs = data?.recommendations || [];

  if (recs.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <CardTitle className="text-base">{t("recommendations")}</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-3 w-3 ${isFetching ? "animate-spin" : ""}`} />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6">
            <Zap className="mb-2 h-8 w-8 text-brand-teal" />
            <p className="text-sm font-medium">{t("allClear")}</p>
            <p className="text-xs text-muted-foreground">
              {t("noRecommendations")}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-base">
          {t("recommendations")}
          <Badge variant="secondary" className="ml-2 text-xs">
            {recs.length}
          </Badge>
        </CardTitle>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`h-3 w-3 ${isFetching ? "animate-spin" : ""}`} />
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        {recs.map((rec) => {
          const config = typeConfig[rec.type];
          const Icon = config.icon;
          return (
            <div
              key={rec.id}
              className={`rounded-lg border p-3 ${config.bg} transition-colors`}
            >
              <div className="flex items-start gap-3">
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${config.color}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{rec.title}</p>
                    <Badge variant={priorityVariant[rec.priority]} className="text-[10px] px-1.5 py-0">
                      {rec.priority}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                    {rec.description}
                  </p>
                  {rec.action_label && rec.action_url && (
                    <Link href={rec.action_url}>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-1 h-6 text-xs px-2"
                      >
                        {rec.action_label}
                        <ChevronRight className="ml-1 h-3 w-3" />
                      </Button>
                    </Link>
                  )}
                </div>
                {rec.count != null && (
                  <Badge variant="outline" className="text-xs shrink-0">
                    {rec.count}
                  </Badge>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
