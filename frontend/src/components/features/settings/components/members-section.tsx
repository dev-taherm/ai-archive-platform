"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, UserMinus } from "lucide-react";
import { roleColors } from "@/lib/constants";

interface MembersSectionProps {
  members: any[];
  currentUserId?: string;
  onRemoveMember: (id: string) => void;
  isAdmin: boolean;
  t: Function;
}

export default function MembersSection({
  members,
  currentUserId,
  onRemoveMember,
  isAdmin,
  t,
}: MembersSectionProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Users className="h-5 w-5" />
          {t("members")}
        </h3>
        <Badge variant="secondary">{members.length}</Badge>
      </div>

      {members.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("noMembers")}</p>
      ) : (
        <div className="space-y-2">
          {members.map((m: any) => (
            <div
              key={m.id}
              className="flex items-center justify-between rounded-md border p-3"
            >
              <div className="flex-1">
                <p className="text-sm font-medium">
                  {m.user_email}
                  {m.user === currentUserId && (
                    <span className="ml-2 text-xs text-muted-foreground">{t("you")}</span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("memberInfo", { username: m.user_username, date: new Date(m.joined_at).toLocaleDateString() })}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={roleColors[m.role]}>
                  {m.role}
                </Badge>
                {isAdmin && m.role !== "owner" && m.user !== currentUserId && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive"
                    onClick={() => onRemoveMember(m.id)}
                  >
                    <UserMinus className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
