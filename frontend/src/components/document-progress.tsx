"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";
import {
  documentStatusProgress,
  documentStatusLabel,
  documentStatusColor,
} from "@/lib/constants";
import type { Document } from "@/types/api";

function formatDuration(totalSeconds: number): string {
  const s = Math.floor(totalSeconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const sec = s % 60;
  if (m < 60) return `${m}m ${sec}s`;
  const h = Math.floor(m / 60);
  const min = m % 60;
  return `${h}h ${min}m`;
}

interface DocumentProgressProps {
  status: Document["processing_status"];
  createdAt?: string;
  compact?: boolean;
  className?: string;
}

export default function DocumentProgress({
  status,
  createdAt,
  compact = false,
  className,
}: DocumentProgressProps) {
  const percent = documentStatusProgress[status] ?? 0;
  const label = documentStatusLabel[status] ?? status;
  const barColor = documentStatusColor[status] ?? "";
  const isActive = !["completed", "failed"].includes(status);

  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isActive || !createdAt) return;
    const start = new Date(createdAt).getTime();
    const tick = () => setElapsed((Date.now() - start) / 1000);
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [isActive, createdAt]);

  return (
    <div className={cn("w-full", className)}>
      <Progress
        value={percent}
        indicatorClassName={barColor}
        animated={isActive}
        className={cn(compact ? "h-1.5" : "h-2")}
      />
      <div className={cn(
        "flex items-center gap-2",
        compact ? "mt-0.5" : "mt-1",
      )}>
        <p className={cn(
          "text-muted-foreground",
          compact ? "text-[10px] leading-tight" : "text-xs"
        )}>
          {label}
        </p>
        {isActive && elapsed > 0 && (
          <p className={cn(
            "text-muted-foreground tabular-nums",
            compact ? "text-[10px] leading-tight" : "text-xs"
          )}>
            {formatDuration(elapsed)}
          </p>
        )}
      </div>
    </div>
  );
}
