from __future__ import annotations

import logging
from typing import Any

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.organizations.models import Invitation, Membership, Organization
from apps.organizations.permissions import IsOrgAdmin, IsOrgMember
from apps.organizations.serializers import (
    InvitationCreateSerializer,
    InvitationSerializer,
    MembershipSerializer,
    OrganizationSerializer,
)
from apps.organizations.services import OrgService

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    """CRUD for the current user's organization."""

    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get_permissions(self):
        if self.action == "create_organization":
            return [IsAuthenticated()]
        if self.action in ("current", "list", "retrieve"):
            return [IsAuthenticated(), IsOrgMember()]
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsOrgAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.organization_id:
            return Organization.objects.none()
        return Organization.objects.filter(id=user.organization_id)

    @action(detail=False, methods=["get", "patch"])
    def current(self, request: Request) -> Response:
        """Get or update the user's current organization."""
        org = request.user.organization
        if not org:
            return Response({"detail": "No organization."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "PATCH":
            if not OrgService.is_org_admin(request.user, org):
                return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
            serializer = OrganizationSerializer(org, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(OrganizationSerializer(org).data)

    @action(detail=False, methods=["post"])
    def create_organization(self, request: Request) -> Response:
        """Create a new organization and make the user the owner."""
        try:
            serializer = OrganizationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            org = OrgService.create_organization(
                name=serializer.validated_data["name"],
                slug=serializer.validated_data["slug"],
                owner=request.user,
                description=serializer.validated_data.get("description", ""),
            )
            return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Failed to create organization")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MembershipViewSet(viewsets.ModelViewSet):
    """Manage organization members."""

    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        user = self.request.user
        if not user.organization_id:
            return Membership.objects.none()
        return Membership.objects.filter(
            organization=user.organization,
        ).select_related("user")

    def get_permissions(self):
        if self.action in ("create", "destroy", "partial_update"):
            return [IsAuthenticated(), IsOrgAdmin()]
        return [IsAuthenticated(), IsOrgMember()]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsOrgAdmin])
    def remove(self, request: Request, pk: str | None = None) -> Response:
        """Remove a member from the organization."""
        membership = self.get_object()
        if membership.role == Membership.OrgRole.OWNER:
            return Response(
                {"detail": "Cannot remove the owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        OrgService.remove_member(membership.organization, membership.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationViewSet(viewsets.ModelViewSet):
    """Manage organization invitations."""

    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        user = self.request.user
        if not user.organization_id:
            return Invitation.objects.none()
        return Invitation.objects.filter(organization=user.organization)

    def get_permissions(self):
        if self.action in ("create", "destroy", "partial_update"):
            return [IsAuthenticated(), IsOrgAdmin()]
        return [IsAuthenticated(), IsOrgMember()]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = request.user.organization
        if not org:
            return Response(
                {"detail": "No organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation = OrgService.create_invitation(
            organization=org,
            email=serializer.validated_data["email"],
            role=serializer.validated_data.get("role", Membership.OrgRole.MEMBER),
            invited_by=request.user,
        )
        return Response(
            InvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def accept(self, request: Request) -> Response:
        """Accept an invitation by token."""
        token = request.data.get("token")
        if not token:
            return Response(
                {"detail": "Token required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = OrgService.accept_invitation(token, request.user)
        if not membership:
            return Response(
                {"detail": "Invalid or expired invitation."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(MembershipSerializer(membership).data)
