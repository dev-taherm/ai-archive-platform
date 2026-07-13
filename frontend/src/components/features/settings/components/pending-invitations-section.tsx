"use client";

import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

interface PendingInvitationsSectionProps {
  invitations: any[];
  onRevoke: (id: string) => void;
  t: Function;
}

export default function PendingInvitationsSection({
  invitations,
  onRevoke,
  t,
}: PendingInvitationsSectionProps) {
  const pending = invitations.filter((inv) => inv.status === "pending");

  if (pending.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{t("pendingInvitations")}</h3>
      <div className="space-y-2">
        {pending.map((inv) => (
          <div
            key={inv.id}
            className="flex items-center justify-between rounded-md border p-3"
          >
            <div className="flex-1">
              <p className="text-sm font-medium">{inv.email}</p>
              <p className="text-xs text-muted-foreground">
                {t("invitationInfo", { role: inv.role, date: new Date(inv.expires_at).toLocaleDateString() })}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive"
              onClick={() => onRevoke(inv.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
