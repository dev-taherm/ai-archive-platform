"use client";

import { formatDateTime } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  FileText,
  Search,
  Trash2,
  RefreshCw,
  Upload,
  Settings,
  FolderOpen,
} from "lucide-react";
import type { ActivityItem } from "@/types/api";

const iconMap: Record<string, typeof FileText> = {
  upload: Upload,
  create: FileText,
  search: Search,
  delete: Trash2,
  update: RefreshCw,
  process: RefreshCw,
  index: FolderOpen,
  classify: Settings,
  scan: FolderOpen,
  rename: RefreshCw,
  move: FolderOpen,
  copy: FileText,
  download: FileText,
};

interface RecentActivityProps {
  activities: ActivityItem[];
}

export function RecentActivity({ activities }: RecentActivityProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activities.length === 0 && (
            <p className="text-sm text-muted-foreground">No recent activity</p>
          )}
          {activities.map((activity) => {
            const Icon = iconMap[activity.action] || FileText;
            return (
              <div
                key={activity.id}
                className="flex items-start gap-3 rounded-lg border p-3"
              >
                <div className="rounded-md bg-muted p-2">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium">
                    {activity.action}
                    {activity.resource_id && (
                      <span className="text-muted-foreground">
                        {" "}
                        — {String(activity.resource_id).slice(0, 8)}
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {activity.user_email && (
                      <span className="mr-2">{activity.user_email}</span>
                    )}
                    {formatDateTime(activity.created_at)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
