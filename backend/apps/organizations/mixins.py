"""Mixin and helpers for org-scoped API views."""

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import PermissionDenied


def get_user_organization(user: Any):
    """Return the user's organization or raise PermissionDenied."""
    org = getattr(user, "organization", None)
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
        org = get_user_organization(self.request.user)
        if qs is None:
            qs = self.model_class.objects.all()
        return qs.filter(organization=org)
