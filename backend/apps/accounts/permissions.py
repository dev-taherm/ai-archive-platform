from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    """Allow access only to admin users.

    Grants full access to all resources.  An admin is any user whose
    ``role`` is ``User.Role.ADMIN`` **or** who is flagged as a Django
    superuser.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin
        )


class IsArchivist(BasePermission):
    """Allow access to archivist and admin users.

    Archivists can manage files, documents, and workflows.  This role
    implicitly includes all admin privileges (admins pass this check).
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_archivist
        )


class IsResearcher(BasePermission):
    """Allow access to researcher, archivist, and admin users.

    Researchers can search, view, and export records.  The check
    mirrors the ``is_archivist`` property on the ``User`` model which
    already includes the admin role.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role
            in (
                request.user.Role.ADMIN,
                request.user.Role.ARCHIVIST,
                request.user.Role.RESEARCHER,
            )
        )


class IsViewer(BasePermission):
    """Allow access to any authenticated user.

    Viewers have read-only access.  Write operations are denied
    regardless of role.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method not in SAFE_METHODS:
            return False
        return True


class IsOwnerOrAdmin(BasePermission):
    """Object-level permission: allow the owner of an object or any admin.

    The checked object must expose an ``owner`` attribute or the view
    must define an ``owner_field`` attribute that points to the field
    holding the user foreign key (default ``"user"``).

    Object-level check falls back to the owner attribute / field; the
    admin override is evaluated first for early exit.
    """

    def has_object_permission(
        self, request: Any, view: Any, obj: Any
    ) -> bool:
        # Admins always pass.
        if request.user and request.user.is_admin:
            return True

        owner_field: str = getattr(view, "owner_field", "user")
        owner = getattr(obj, owner_field, None)
        return owner == request.user
