import { useTranslation } from "react-i18next";
import { Card, CardContent } from "../components/ui/card";
import { FileText, Check, Clock, AlertTriangle } from "lucide-react";

interface StatsCardsProps {
  total: number;
  completed: number;
  synced: number;
  pending: number;
  failed: number;
}

export function StatsCards({ total, completed, synced, pending, failed }: StatsCardsProps) {
  const { t } = useTranslation();

  const cards = [
    {
      title: t("stats.total"),
      value: total,
      icon: FileText,
      color: "text-blue-600",
    },
    {
      title: t("stats.completed"),
      value: completed,
      icon: Check,
      color: "text-green-600",
    },
    {
      title: t("stats.synced"),
      value: synced,
      icon: Check,
      color: "text-emerald-600",
    },
    {
      title: t("stats.pending"),
      value: pending,
      icon: Clock,
      color: "text-yellow-600",
    },
    {
      title: t("stats.failed"),
      value: failed,
      icon: AlertTriangle,
      color: "text-red-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">{card.title}</p>
                <p className="text-2xl font-bold">{card.value}</p>
              </div>
              <card.icon className={`h-8 w-8 ${card.color} opacity-50`} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
