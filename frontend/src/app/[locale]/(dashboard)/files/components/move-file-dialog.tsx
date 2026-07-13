"use client";

import type { FileRecord, Agent } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Loader2 } from "lucide-react";

interface MoveFileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  file: FileRecord | null;
  agents: Agent[];
  moveMode: "agent" | "folder";
  moveTargetAgent: string;
  moveSourcePath: string;
  moveTargetPath: string;
  onMoveModeChange: (mode: "agent" | "folder") => void;
  onMoveTargetAgentChange: (v: string) => void;
  onMoveSourcePathChange: (v: string) => void;
  onMoveTargetPathChange: (v: string) => void;
  onConfirm: () => void;
  isMoving: boolean;
  t: Function;
  tc: Function;
}

export default function MoveFileDialog({
  open,
  onOpenChange,
  agents,
  moveMode,
  moveTargetAgent,
  moveSourcePath,
  moveTargetPath,
  onMoveModeChange,
  onMoveTargetAgentChange,
  onMoveSourcePathChange,
  onMoveTargetPathChange,
  onConfirm,
  isMoving,
  t,
  tc,
}: MoveFileDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("moveFileTitle")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t("moveFileDescription")}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="space-y-4 py-4">
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={moveMode === "agent" ? "default" : "outline"}
              onClick={() => onMoveModeChange("agent")}
            >
              {t("moveToDevice")}
            </Button>
            <Button
              size="sm"
              variant={moveMode === "folder" ? "default" : "outline"}
              onClick={() => onMoveModeChange("folder")}
            >
              {t("moveToFolder")}
            </Button>
          </div>

          {moveMode === "agent" ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">{t("targetDevice")}</p>
              <select
                value={moveTargetAgent}
                onChange={(e) => onMoveTargetAgentChange(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="">{t("selectDevice")}</option>
                {agents.map((a) => (
                  <option key={a.agent_id} value={a.agent_id}>
                    {a.name} ({a.agent_id})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="space-y-2">
              <div>
                <p className="text-sm text-muted-foreground mb-1">{t("sourcePathPrefix")}</p>
                <Input
                  placeholder={t("sourcePathPlaceholder")}
                  value={moveSourcePath}
                  onChange={(e) => onMoveSourcePathChange(e.target.value)}
                />
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">{t("targetPathPrefix")}</p>
                <Input
                  placeholder={t("targetPathPlaceholder")}
                  value={moveTargetPath}
                  onChange={(e) => onMoveTargetPathChange(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>
            {isMoving && (
              <Loader2 className="h-4 w-4 animate-spin mr-1 text-brand-teal" />
            )}
            {t("moveFile")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
