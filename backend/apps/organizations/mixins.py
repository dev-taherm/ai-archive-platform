"""Mixin and helpers for org-scoped API views."""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.exceptions import PermissionDenied

from apps.organizations.models import Organization


def get_user_organization(user: Any, request: Any = None) -> Organization:
    """Return the user's current organization or raise PermissionDenied.

    Resolution order:
    1. JWT ``current_org_id`` claim (from ``request.auth``)
    2. ``user.current_organization`` FK
    3. Raises PermissionDenied if neither is set
    """
    org = None

    # 1. Try JWT claim first
    if request is not None and hasattr(request, "auth") and request.auth is not None:
        raw_org_id = request.auth.get("current_org_id")
        if raw_org_id:
            try:
                org = Organization.objects.get(id=uuid.UUID(str(raw_org_id)))
            except (Organization.DoesNotExist, ValueError):
                org = None

    # 2. Fall back to FK
    if org is None:
        org = getattr(user, "current_organization", None)

    if org is None:
        raise PermissionDenied(
            "You must belong to an organization to access this resource."
        )
    return org


class OrgScopedMixin:
    """Mixin that provides get_queryset filtered by the user's organization.

    Views must define ``model_class`` (the Django model) or override
    ``get_queryset`` to use ``self._org_qs()``.
    """

    model_class = None  # Override in subclass

    def _org_qs(self, qs=None):
        """Filter a queryset (or the model's default manager) by org."""
        org = get_user_organization(self.request.user, self.request)
        if qs is None:
            qs = self.model_class.objects.all()
        return qs.filter(organization=org)
