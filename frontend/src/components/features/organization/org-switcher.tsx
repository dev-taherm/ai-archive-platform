"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useSwitchOrganization } from "@/hooks/use-organization";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Building2, Check, ChevronDown, Loader2 } from "lucide-react";
import type { OrgMembership } from "@/types/api";

export default function OrgSwitcher() {
  const { user } = useAuth();
  const { toast } = useToast();
  const switchOrg = useSwitchOrganization();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  const orgs: OrgMembership[] = user.organizations || [];
  const currentOrg = orgs.find((o) => o.id === user.current_organization);

  const handleSwitch = async (orgId: string) => {
    if (orgId === user.current_organization) {
      setOpen(false);
      return;
    }
    try {
      await switchOrg.mutateAsync(orgId);
      toast({ title: "Switched organization" });
    } catch {
      toast({ title: "Failed to switch organization", variant: "destructive" });
    }
    setOpen(false);
  };

  if (orgs.length <= 1) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 text-sm">
        <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="truncate font-medium">{currentOrg?.name || "No organization"}</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        className="w-full justify-start gap-2 px-3 py-2 h-auto text-sm font-normal"
        onClick={() => setOpen(!open)}
      >
        <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="truncate flex-1 text-left">{currentOrg?.name || "Select organization"}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </Button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute bottom-full left-0 right-0 z-50 mb-1 rounded-md border bg-popover p-1 shadow-md">
            {orgs.map((org) => (
              <button
                key={org.id}
                className={`flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground ${
                  org.id === user.current_organization ? "bg-accent" : ""
                }`}
                onClick={() => handleSwitch(org.id)}
                disabled={switchOrg.isPending}
              >
                {switchOrg.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : org.id === user.current_organization ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  <span className="h-3.5 w-3.5" />
                )}
                <span className="truncate">{org.name}</span>
                <span className="ml-auto text-xs text-muted-foreground capitalize">{org.role}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
