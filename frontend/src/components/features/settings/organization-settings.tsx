"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/hooks/use-auth";
import {
  useOrganization,
  useOrganizations,
  useUpdateOrganization,
  useOrgMembers,
  useOrgInvitations,
  useInviteMember,
  useRevokeInvitation,
  useRemoveMember,
  useCreateOrganization,
  useLeaveOrganization,
  useSwitchOrganization,
} from "@/hooks/use-organization";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { roleColors } from "@/lib/constants";
import CreateOrganizationForm from "./components/create-organization-form";
import OrgInfoSection from "./components/org-info-section";
import MembersSection from "./components/members-section";
import InviteMemberSection from "./components/invite-member-section";
import PendingInvitationsSection from "./components/pending-invitations-section";
import OrganizationSwitcher from "./components/organization-switcher";

export default function OrganizationSettings() {
  const t = useTranslations("settings");
  const tc = useTranslations("common");
  const { user } = useAuth();
  const { toast } = useToast();
  const { data: org, isLoading: orgLoading } = useOrganization();
  const { data: allOrgs = [] } = useOrganizations();
  const updateOrg = useUpdateOrganization();
  const createOrg = useCreateOrganization();
  const { data: members = [] } = useOrgMembers();
  const { data: invitations = [] } = useOrgInvitations();
  const inviteMember = useInviteMember();
  const revokeInvitation = useRevokeInvitation();
  const removeMember = useRemoveMember();
  const leaveOrg = useLeaveOrganization();
  const switchOrg = useSwitchOrganization();

  const [orgName, setOrgName] = useState(org?.name || "");
  const [orgDescription, setOrgDescription] = useState(org?.description || "");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");

  const isAdmin = user?.org_role === "owner" || user?.org_role === "admin";

  if (orgLoading) {
    return <div className="text-muted-foreground">{t("loadingOrganization")}</div>;
  }

  if (!org) {
    const handleCreateOrg = async (name: string, slug: string, description: string) => {
      if (!name || !slug) return;
      try {
        await createOrg.mutateAsync({ name, slug, description: description || undefined });
        toast({ title: t("orgCreated") });
      } catch (err: any) {
        const msg = err?.response?.data?.detail || err?.response?.data?.slug?.[0] || t("orgCreateFailed");
        toast({ title: msg, variant: "destructive" });
      }
    };
    return <CreateOrganizationForm onCreate={handleCreateOrg} creating={createOrg.isPending} t={t} tc={tc} />;
  }

  const handleUpdateOrg = async () => {
    if (!orgName.trim()) return;
    try {
      await updateOrg.mutateAsync({ name: orgName.trim(), description: orgDescription.trim() });
      toast({ title: t("orgUpdated") });
    } catch {
      toast({ title: t("orgUpdateFailed"), variant: "destructive" });
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    try {
      await inviteMember.mutateAsync({ email: inviteEmail.trim(), role: inviteRole });
      setInviteEmail("");
      toast({ title: t("invitationSent", { email: inviteEmail }) });
    } catch {
      toast({ title: t("invitationSendFailed"), variant: "destructive" });
    }
  };

  const handleRevokeInvitation = async (id: string) => {
    try { await revokeInvitation.mutateAsync(id); toast({ title: t("invitationRevoked") }); }
    catch { toast({ title: t("invitationRevokeFailed"), variant: "destructive" }); }
  };

  const handleRemoveMember = async (id: string) => {
    try { await removeMember.mutateAsync(id); toast({ title: t("memberRemoved") }); }
    catch { toast({ title: t("memberRemoveFailed"), variant: "destructive" }); }
  };

  const handleLeaveOrg = async () => {
    try { await leaveOrg.mutateAsync(); toast({ title: t("leftOrganization") }); }
    catch (err: any) { toast({ title: err?.response?.data?.detail || t("leaveOrgFailed"), variant: "destructive" }); }
  };

  const handleSwitchOrg = async (orgId: string) => {
    try { await switchOrg.mutateAsync(orgId); toast({ title: t("orgSwitched") }); }
    catch { toast({ title: t("orgSwitchFailed"), variant: "destructive" }); }
  };

  return (
    <div className="space-y-8">
      <OrgInfoSection
        org={org} orgName={orgName} orgDescription={orgDescription}
        onNameChange={setOrgName} onDescriptionChange={setOrgDescription}
        onSave={handleUpdateOrg} saving={updateOrg.isPending} isAdmin={isAdmin} t={t}
      />
      <MembersSection
        members={members} currentUserId={user?.id}
        onRemoveMember={handleRemoveMember} isAdmin={isAdmin} t={t}
      />
      {isAdmin && (
        <InviteMemberSection
          email={inviteEmail} role={inviteRole}
          onEmailChange={setInviteEmail} onRoleChange={setInviteRole}
          onInvite={handleInvite} inviting={inviteMember.isPending} t={t}
        />
      )}
      <PendingInvitationsSection invitations={invitations} onRevoke={handleRevokeInvitation} t={t} />
      <OrganizationSwitcher
        organizations={user?.organizations || []} currentOrgId={user?.current_organization || ""}
        onSwitch={handleSwitchOrg} switching={switchOrg.isPending} t={t}
      />
      {user?.org_role !== "owner" && user?.current_organization && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-destructive">{t("dangerZone")}</h3>
          <div className="rounded-md border border-destructive/20 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{t("leaveOrganization")}</p>
                <p className="text-xs text-muted-foreground">{t("leaveOrgDesc")}</p>
              </div>
              <Button variant="destructive" size="sm" onClick={handleLeaveOrg} disabled={leaveOrg.isPending}>
                <LogOut className="mr-1 h-3.5 w-3.5" />
                {leaveOrg.isPending ? t("leaving") : t("leave")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
