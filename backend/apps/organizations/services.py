from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Invitation, Membership, Organization

User = get_user_model()

logger = logging.getLogger(__name__)


class OrgService:
    """Manages organizations, memberships, and invitations."""

    @staticmethod
    def create_organization(
        name: str,
        slug: str,
        owner: User,
        description: str = "",
    ) -> Organization:
        """Create an org and add the owner as a member.

        In multi-org mode, the user keeps their existing memberships.
        The new org becomes their current organization.
        """
        with transaction.atomic():
            org = Organization.objects.create(
                name=name,
                slug=slug,
                description=description,
            )
            Membership.objects.create(
                user=owner,
                organization=org,
                role=Membership.OrgRole.OWNER,
            )
            owner.current_organization = org
            owner.save(update_fields=["current_organization"])
            return org

    @staticmethod
    def add_member(
        organization: Organization,
        user: User,
        role: str = Membership.OrgRole.MEMBER,
    ) -> Membership:
        """Add a user to an organization."""
        membership, created = Membership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={"role": role},
        )
        if not user.current_organization_id:
            user.current_organization = organization
            user.save(update_fields=["current_organization"])
        return membership

    @staticmethod
    def remove_member(organization: Organization, user: User) -> bool:
        """Remove a user from an organization."""
        deleted, _ = Membership.objects.filter(
            user=user,
            organization=organization,
        ).exclude(role=Membership.OrgRole.OWNER).delete()
        return deleted > 0

    @staticmethod
    def get_user_org(user: User) -> Organization | None:
        """Return the user's current organization."""
        return user.current_organization

    @staticmethod
    def is_org_member(user: User, organization: Organization) -> bool:
        """Check if a user belongs to an organization."""
        return Membership.objects.filter(
            user=user,
            organization=organization,
        ).exists()

    @staticmethod
    def is_org_admin(user: User, organization: Organization) -> bool:
        """Check if a user is an admin or owner of an organization."""
        return Membership.objects.filter(
            user=user,
            organization=organization,
            role__in=(Membership.OrgRole.OWNER, Membership.OrgRole.ADMIN),
        ).exists()

    @staticmethod
    def get_org_members(organization: Organization):
        """Return all memberships for an organization."""
        return Membership.objects.filter(
            organization=organization,
        ).select_related("user")

    @staticmethod
    def create_invitation(
        organization: Organization,
        email: str,
        role: str = Membership.OrgRole.MEMBER,
        invited_by: User | None = None,
        expires_days: int = 7,
    ) -> Invitation:
        """Create an invitation token for an email and send the invite."""
        token = secrets.token_hex(32)
        expires_at = timezone.now() + timedelta(days=expires_days)
        invitation = Invitation.objects.create(
            organization=organization,
            email=email,
            role=role,
            invited_by=invited_by,
            token=token,
            expires_at=expires_at,
        )

        # Dispatch invitation email asynchronously
        try:
            from apps.organizations.tasks import send_invitation_email

            invited_by_name = (
                f"{invited_by.first_name} {invited_by.last_name}".strip()
                if invited_by
                else "An administrator"
            )
            send_invitation_email.delay(
                invitation_id=str(invitation.id),
                organization_name=organization.name,
                invited_email=email,
                role=role,
                invited_by_name=invited_by_name,
                token=token,
            )
        except Exception:
            logger.warning("Failed to dispatch invitation email to %s", email)

        return invitation

    @staticmethod
    def accept_invitation(token: str, user: User) -> Membership | None:
        """Accept an invitation by token. Returns the new Membership or None."""
        try:
            invitation = Invitation.objects.get(
                token=token,
                status=Invitation.Status.PENDING,
            )
        except Invitation.DoesNotExist:
            return None

        if invitation.expires_at < timezone.now():
            invitation.status = Invitation.Status.EXPIRED
            invitation.save(update_fields=["status"])
            return None

        with transaction.atomic():
            invitation.status = Invitation.Status.ACCEPTED
            invitation.save(update_fields=["status"])

            membership, _ = Membership.objects.get_or_create(
                user=user,
                organization=invitation.organization,
                defaults={"role": invitation.role},
            )
            if not user.current_organization_id:
                user.current_organization = invitation.organization
                user.save(update_fields=["current_organization"])

            return membership
