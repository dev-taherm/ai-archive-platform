"use client";

import type { OrgMembership } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Building2, ArrowRightLeft } from "lucide-react";
import { roleColors } from "@/lib/constants";

interface OrganizationSwitcherProps {
  organizations: OrgMembership[];
  currentOrgId: string;
  onSwitch: (id: string) => void;
  switching: boolean;
  t: Function;
}

export default function OrganizationSwitcher({
  organizations,
  currentOrgId,
  onSwitch,
  switching,
  t,
}: OrganizationSwitcherProps) {
  if (organizations.length <= 1) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <Building2 className="h-5 w-5" />
        {t("yourOrganizations")}
      </h3>
      <div className="space-y-2">
        {organizations.map((o) => (
          <div
            key={o.id}
            className="flex items-center justify-between rounded-md border p-3"
          >
            <div className="flex-1">
              <p className="text-sm font-medium">{o.name}</p>
              <p className="text-xs text-muted-foreground">
                {o.slug} · <span className="capitalize">{o.role}</span>
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={roleColors[o.role]}>
                {o.role}
              </Badge>
              {o.id !== currentOrgId && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onSwitch(o.id)}
                  disabled={switching}
                >
                  <ArrowRightLeft className="mr-1 h-3.5 w-3.5" />
                  {t("switch")}
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
