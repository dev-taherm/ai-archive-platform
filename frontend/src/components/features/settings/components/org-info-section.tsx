"use client";

import { useState } from "react";
import type { Organization } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Copy, Check } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { roleColors } from "@/lib/constants";

interface OrgInfoSectionProps {
  org: Organization;
  orgName: string;
  orgDescription: string;
  onNameChange: (v: string) => void;
  onDescriptionChange: (v: string) => void;
  onSave: () => void;
  saving: boolean;
  isAdmin: boolean;
  t: Function;
}

export default function OrgInfoSection({
  org,
  orgName,
  orgDescription,
  onNameChange,
  onDescriptionChange,
  onSave,
  saving,
  isAdmin,
  t,
}: OrgInfoSectionProps) {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  const copySlug = () => {
    navigator.clipboard.writeText(org.slug);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast({ title: t("inviteLinkCopied") });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t("organization")}</h3>
      </div>

      <div className="space-y-2">
        <label htmlFor="orgName" className="text-sm font-medium">
          {t("name")}
        </label>
        <Input
          id="orgName"
          value={orgName}
          onChange={(e) => onNameChange(e.target.value)}
          className="max-w-md"
          disabled={!isAdmin}
        />
      </div>
      <div className="space-y-2">
        <label htmlFor="orgDescription" className="text-sm font-medium">
          {t("orgDescription")}
        </label>
        <Input
          id="orgDescription"
          value={orgDescription}
          onChange={(e) => onDescriptionChange(e.target.value)}
          className="max-w-md"
          disabled={!isAdmin}
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">{t("slug")}</label>
        <div className="flex items-center gap-2">
          <Input value={org.slug} disabled className="max-w-md" />
          <Button variant="outline" size="icon" onClick={copySlug} className="shrink-0">
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      </div>
      {isAdmin && (
        <Button onClick={onSave} disabled={saving}>
          {saving ? t("saving") : t("saveChanges")}
        </Button>
      )}
    </div>
  );
}
