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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Building2,
  Users,
  Mail,
  Copy,
  Check,
  UserMinus,
  Trash2,
  Plus,
  LogOut,
  ArrowRightLeft,
} from "lucide-react";

const roleColors: Record<string, string> = {
  owner: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  admin: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  member: "bg-gray-100 text-gray-800 dark:bg-gray-800/30 dark:text-gray-300",
};

export default function OrganizationSettings() {
  const t = useTranslations("settings");
  const tc = useTranslations("common");
  const { user } = useAuth();
  const { toast } = useToast();
  const { data: org, isLoading: orgLoading } = useOrganization();
  const { data: allOrgs = [] } = useOrganizations();
  const updateOrg = useUpdateOrganization();
  const createOrg = useCreateOrganization();
  const { data: members = [], isLoading: membersLoading } = useOrgMembers();
  const { data: invitations = [], isLoading: invitationsLoading } = useOrgInvitations();
  const inviteMember = useInviteMember();
  const revokeInvitation = useRevokeInvitation();
  const removeMember = useRemoveMember();
  const leaveOrg = useLeaveOrganization();
  const switchOrg = useSwitchOrganization();

  const [orgName, setOrgName] = useState(org?.name || "");
  const [orgDescription, setOrgDescription] = useState(org?.description || "");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [copied, setCopied] = useState(false);

  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgSlug, setNewOrgSlug] = useState("");
  const [newOrgDescription, setNewOrgDescription] = useState("");

  const isAdmin = user?.org_role === "owner" || user?.org_role === "admin";

  if (orgLoading) {
    return <div className="text-muted-foreground">{t("loadingOrganization")}</div>;
  }

  if (!org) {
    const handleCreateOrg = async () => {
      if (!newOrgName.trim() || !newOrgSlug.trim()) return;
      try {
        await createOrg.mutateAsync({
          name: newOrgName.trim(),
          slug: newOrgSlug.trim(),
          description: newOrgDescription.trim() || undefined,
        });
        toast({ title: t("orgCreated") });
      } catch (err: any) {
        const msg =
          err?.response?.data?.detail ||
          err?.response?.data?.slug?.[0] ||
          t("orgCreateFailed");
        toast({ title: msg, variant: "destructive" });
      }
    };

    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            {t("createOrganization")}
          </h3>
          <p className="text-sm text-muted-foreground">
            {t("noOrgDescription")}
          </p>
        </div>

        <div className="space-y-4 max-w-md">
          <div className="space-y-2">
            <label htmlFor="newOrgName" className="text-sm font-medium">
              {t("orgName")}
            </label>
            <Input
              id="newOrgName"
              placeholder={t("orgNamePlaceholder")}
              value={newOrgName}
              onChange={(e) => {
                setNewOrgName(e.target.value);
                if (!newOrgSlug) {
                  setNewOrgSlug(
                    e.target.value
                      .toLowerCase()
                      .replace(/[^a-z0-9]+/g, "-")
                      .replace(/^-|-$/g, "")
                  );
                }
              }}
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="newOrgSlug" className="text-sm font-medium">
              {t("slug")}
            </label>
            <Input
              id="newOrgSlug"
              placeholder={t("slugPlaceholder")}
              value={newOrgSlug}
              onChange={(e) =>
                setNewOrgSlug(
                  e.target.value
                    .toLowerCase()
                    .replace(/[^a-z0-9-]/g, "")
                    .replace(/--+/g, "-")
                )
              }
            />
            <p className="text-xs text-muted-foreground">
              {t("slugHelp")}
            </p>
          </div>
          <div className="space-y-2">
            <label htmlFor="newOrgDescription" className="text-sm font-medium">
              {t("orgDescription")} <span className="text-muted-foreground">{tc("optional")}</span>
            </label>
            <Input
              id="newOrgDescription"
              placeholder={t("orgDescriptionPlaceholder")}
              value={newOrgDescription}
              onChange={(e) => setNewOrgDescription(e.target.value)}
            />
          </div>
          <Button
            onClick={handleCreateOrg}
            disabled={createOrg.isPending || !newOrgName.trim() || !newOrgSlug.trim()}
          >
            {createOrg.isPending ? t("creating") : t("createOrganization")}
          </Button>
        </div>
      </div>
    );
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
    try {
      await revokeInvitation.mutateAsync(id);
      toast({ title: t("invitationRevoked") });
    } catch {
      toast({ title: t("invitationRevokeFailed"), variant: "destructive" });
    }
  };

  const handleRemoveMember = async (id: string) => {
    try {
      await removeMember.mutateAsync(id);
      toast({ title: t("memberRemoved") });
    } catch {
      toast({ title: t("memberRemoveFailed"), variant: "destructive" });
    }
  };

  const handleLeaveOrg = async () => {
    try {
      await leaveOrg.mutateAsync();
      toast({ title: t("leftOrganization") });
    } catch (err: any) {
      const msg = err?.response?.data?.detail || t("leaveOrgFailed");
      toast({ title: msg, variant: "destructive" });
    }
  };

  const handleSwitchOrg = async (orgId: string) => {
    try {
      await switchOrg.mutateAsync(orgId);
      toast({ title: t("orgSwitched") });
    } catch {
      toast({ title: t("orgSwitchFailed"), variant: "destructive" });
    }
  };

  const copyInviteLink = () => {
    navigator.clipboard.writeText(`${window.location.origin}/invitations/accept?token=pending`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast({ title: t("inviteLinkCopied") });
  };

  return (
    <div className="space-y-8">
      {/* Org Info */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">{t("organization")}</h3>
          <Badge variant="outline" className={roleColors[user?.org_role || "member"]}>
            {user?.org_role}
          </Badge>
        </div>

        <div className="space-y-2">
          <label htmlFor="orgName" className="text-sm font-medium">
            {t("name")}
          </label>
          <Input
            id="orgName"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
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
            onChange={(e) => setOrgDescription(e.target.value)}
            className="max-w-md"
            disabled={!isAdmin}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">{t("slug")}</label>
          <div className="flex items-center gap-2">
            <Input value={org.slug} disabled className="max-w-md" />
            <Button variant="outline" size="icon" onClick={copyInviteLink} className="shrink-0">
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </Button>
          </div>
        </div>
        {isAdmin && (
          <Button onClick={handleUpdateOrg} disabled={updateOrg.isPending}>
            {updateOrg.isPending ? t("saving") : t("saveChanges")}
          </Button>
        )}
      </div>

      {/* Members */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Users className="h-5 w-5" />
            {t("members")}
          </h3>
          <Badge variant="secondary">{members.length}</Badge>
        </div>

        {membersLoading ? (
          <p className="text-sm text-muted-foreground">{t("loadingMembers")}</p>
        ) : members.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("noMembers")}</p>
        ) : (
          <div className="space-y-2">
            {members.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between rounded-md border p-3"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    {m.user_email}
                    {m.user === user?.id && (
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
                  {isAdmin && m.role !== "owner" && m.user !== user?.id && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => handleRemoveMember(m.id)}
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

      {/* Invite */}
      {isAdmin && (
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
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleInvite()}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="inviteRole" className="text-sm font-medium">
                {t("role")}
              </label>
              <select
                id="inviteRole"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors"
              >
                <option value="member">{t("member")}</option>
                <option value="admin">{t("admin")}</option>
              </select>
            </div>
            <Button
              onClick={handleInvite}
              disabled={inviteMember.isPending || !inviteEmail.trim()}
            >
              <Plus className="mr-1 h-3.5 w-3.5" />
              {inviteMember.isPending ? t("sending") : t("invite")}
            </Button>
          </div>
        </div>
      )}

      {/* Pending Invitations */}
      {invitations.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">{t("pendingInvitations")}</h3>
          <div className="space-y-2">
            {invitations
              .filter((inv) => inv.status === "pending")
              .map((inv) => (
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
                  {isAdmin && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => handleRevokeInvitation(inv.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Your Organizations */}
      {user?.organizations && user.organizations.length > 1 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            {t("yourOrganizations")}
          </h3>
          <div className="space-y-2">
            {user.organizations.map((o) => (
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
                  {o.id !== user.current_organization && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleSwitchOrg(o.id)}
                      disabled={switchOrg.isPending}
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
      )}

      {/* Leave Organization */}
      {user?.org_role !== "owner" && user?.current_organization && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-destructive">{t("dangerZone")}</h3>
          <div className="rounded-md border border-destructive/20 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{t("leaveOrganization")}</p>
                <p className="text-xs text-muted-foreground">
                  {t("leaveOrgDesc")}
                </p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleLeaveOrg}
                disabled={leaveOrg.isPending}
              >
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
