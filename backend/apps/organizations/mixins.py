"""Mixin and helpers for org-scoped API views.

Supports two data scopes:
- **personal**: data is owned by the user (``owner=user``, ``organization=NULL``)
- **organization**: data is shared within the org (``organization=org``)

The scope is determined by:
1. ``?scope=personal`` or ``?scope=organization`` query parameter
2. Default: ``organization`` if user has an org, ``personal`` otherwise
"""

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


def get_user_scope(user: Any, request: Any) -> str:
    """Return ``'personal'`` or ``'organization'`` based on query param or user state.

    Resolution:
    1. ``?scope=personal`` or ``?scope=organization`` query parameter
    2. ``'organization'`` if user has an org
    3. ``'personal'`` otherwise (no PermissionDenied raised)
    """
    scope = getattr(request, "query_params", {}).get("scope", None)
    if scope in ("personal", "organization"):
        return scope

    # Auto-detect: org → organization, no org → personal
    try:
        get_user_organization(user, request)
        return "organization"
    except PermissionDenied:
        return "personal"


def get_scoped_queryset(model, user: Any, request: Any):
    """Return a scope-aware queryset for the given model.

    - ``scope=personal`` → ``model.objects.filter(owner=user)``
    - ``scope=organization`` → ``model.objects.filter(organization=org)``

    Raises PermissionDenied only when scope is explicitly ``'organization'``
    and the user has no org.
    """
    scope = get_user_scope(user, request)
    qs = model.objects.all()
    if scope == "personal":
        return qs.filter(owner=user)
    org = get_user_organization(user, request)
    return qs.filter(organization=org)


class OrgScopedMixin:
    """Mixin that provides get_queryset filtered by the user's scope.

    Views must define ``model_class`` (the Django model) or override
    ``get_queryset`` to use ``self._org_qs()``.

    The scope is determined by ``?scope=personal|organization`` query param,
    defaulting to ``'organization'`` if user has an org, ``'personal'`` otherwise.
    """

    model_class = None  # Override in subclass

    def _org_qs(self, qs=None):
        """Filter a queryset (or the model's default manager) by scope."""
        if qs is None:
            qs = self.model_class.objects.all()
        scope = get_user_scope(self.request.user, self.request)
        if scope == "personal":
            return qs.filter(owner=self.request.user)
        org = get_user_organization(self.request.user, self.request)
        return qs.filter(organization=org)
