"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Mail, Plus } from "lucide-react";

interface InviteMemberSectionProps {
  email: string;
  role: string;
  onEmailChange: (v: string) => void;
  onRoleChange: (v: string) => void;
  onInvite: () => void;
  inviting: boolean;
  t: Function;
}

export default function InviteMemberSection({
  email,
  role,
  onEmailChange,
  onRoleChange,
  onInvite,
  inviting,
  t,
}: InviteMemberSectionProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <Mail className="h-5 w-5" />
        {t("inviteMember")}
      </h3>
      <div className="flex items-end gap-2">
        <div className="flex-1 space-y-2 max-w-sm">
          <label htmlFor="inviteEmail" className="text-sm font-medium">
            {t("email")}
          </label>
          <Input
            id="inviteEmail"
            type="email"
            placeholder={t("emailPlaceholder")}
            value={email}
            onChange={(e) => onEmailChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onInvite()}
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="inviteRole" className="text-sm font-medium">
            {t("role")}
          </label>
          <select
            id="inviteRole"
            value={role}
            onChange={(e) => onRoleChange(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors"
          >
            <option value="member">{t("member")}</option>
            <option value="admin">{t("admin")}</option>
          </select>
        </div>
        <Button
          onClick={onInvite}
          disabled={inviting || !email.trim()}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          {inviting ? t("sending") : t("invite")}
        </Button>
      </div>
    </div>
  );
}
