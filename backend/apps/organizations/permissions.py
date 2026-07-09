from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission

from apps.organizations.models import Membership


class IsOrgMember(BasePermission):
    """Allow access only if the user belongs to an organization.

    Expects ``request.user`` to have a ``organization`` FK set.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return Membership.objects.filter(
            user=user,
            organization=user.current_organization,
        ).exists()


class IsOrgAdmin(BasePermission):
    """Allow access only to org admins or owners.

    Grants full access within the organization scope.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if not user.current_organization_id:
            return False
        return Membership.objects.filter(
            user=user,
            organization=user.current_organization,
            role__in=(Membership.OrgRole.OWNER, Membership.OrgRole.ADMIN),
        ).exists()


class IsOrgOwner(BasePermission):
    """Allow access only to org owners."""

    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if not user.current_organization_id:
            return False
        return Membership.objects.filter(
            user=user,
            organization=user.current_organization,
            role=Membership.OrgRole.OWNER,
        ).exists()


class IsDataOwnerOrOrgAdmin(BasePermission):
    """Object-level: allow the data owner or an org admin.

    The checked object must expose an ``owner`` attribute or the view
    must define an ``owner_field`` attribute (default ``"owner"``).
    """

    def has_object_permission(
        self, request: Any, view: Any, obj: Any
    ) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # Org admins always pass.
        if user.current_organization_id and Membership.objects.filter(
            user=user,
            organization=user.current_organization,
            role__in=(Membership.OrgRole.OWNER, Membership.OrgRole.ADMIN),
        ).exists():
            return True

        # Check ownership.
        owner_field: str = getattr(view, "owner_field", "owner")
        owner = getattr(obj, owner_field, None)
        return owner == user
