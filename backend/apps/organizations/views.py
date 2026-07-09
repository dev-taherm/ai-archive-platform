from __future__ import annotations

import logging
from typing import Any

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken

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
    """Manage organizations the user belongs to."""

    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create_organization", "list", "switch", "leave"):
            return [IsAuthenticated()]
        if self.action in ("current", "retrieve"):
            return [IsAuthenticated(), IsOrgMember()]
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsOrgAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Return all organizations the user belongs to."""
        return Organization.objects.filter(
            memberships__user=self.request.user,
        ).distinct()

    @action(detail=False, methods=["get", "patch"])
    def current(self, request: Request) -> Response:
        """Get or update the user's current organization."""
        from apps.organizations.mixins import get_user_organization

        try:
            org = get_user_organization(request.user, request)
        except Exception:
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

    @action(detail=False, methods=["post"])
    def switch(self, request: Request) -> Response:
        """Switch the user's current organization.

        Accepts {"organization_id": "..."} and returns a new JWT access token
        with the updated ``current_org_id`` claim.
        """
        org_id = request.data.get("organization_id")
        if not org_id:
            return Response(
                {"detail": "organization_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response(
                {"detail": "Organization not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify membership
        if not Membership.objects.filter(user=request.user, organization=org).exists():
            return Response(
                {"detail": "You are not a member of this organization."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Update current org
        request.user.current_organization = org
        request.user.save(update_fields=["current_organization"])

        # Generate new access token with updated org claim
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(request.user)
        refresh["current_org_id"] = str(org.id)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "organization": OrganizationSerializer(org).data,
        })

    @action(detail=False, methods=["post"])
    def leave(self, request: Request) -> Response:
        """Leave the current organization.

        Owners cannot leave (must transfer ownership or delete the org first).
        After leaving, if the user has other orgs, switches to the most recent one.
        """
        org = request.user.current_organization
        if not org:
            return Response(
                {"detail": "You are not in any organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = Membership.objects.filter(
            user=request.user, organization=org,
        ).first()

        if not membership:
            return Response(
                {"detail": "You are not a member of this organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if membership.role == Membership.OrgRole.OWNER:
            return Response(
                {"detail": "Owner cannot leave. Transfer ownership or delete the organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete membership
        membership.delete()

        # Find another org to switch to, or clear current org
        other_membership = (
            Membership.objects.filter(user=request.user)
            .select_related("organization")
            .order_by("-joined_at")
            .first()
        )

        if other_membership:
            request.user.current_organization = other_membership.organization
        else:
            request.user.current_organization = None
        request.user.save(update_fields=["current_organization"])

        return Response({"detail": "You have left the organization."})


class MembershipViewSet(viewsets.ModelViewSet):
    """Manage organization members."""

    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        from apps.organizations.mixins import get_user_organization

        try:
            org = get_user_organization(self.request.user, self.request)
        except Exception:
            return Membership.objects.none()
        return Membership.objects.filter(
            organization=org,
        ).select_related("user")

    def get_permissions(self):
        if self.action in ("create", "destroy", "partial_update"):
            return [IsAuthenticated(), IsOrgAdmin()]
        return [IsAuthenticated(), IsOrgMember()]

    def perform_create(self, serializer: Any) -> None:
        from apps.organizations.mixins import get_user_organization

        org = get_user_organization(self.request.user, self.request)
        serializer.save(organization=org)

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
        from apps.organizations.mixins import get_user_organization

        try:
            org = get_user_organization(self.request.user, self.request)
        except Exception:
            return Invitation.objects.none()
        return Invitation.objects.filter(organization=org)

    def get_permissions(self):
        if self.action in ("create", "destroy", "partial_update"):
            return [IsAuthenticated(), IsOrgAdmin()]
        return [IsAuthenticated(), IsOrgMember()]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from apps.organizations.mixins import get_user_organization

        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            org = get_user_organization(request.user, request)
        except Exception:
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
