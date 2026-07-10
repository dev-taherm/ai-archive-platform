from __future__ import annotations

from rest_framework import serializers

from apps.organizations.models import Invitation, Membership, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_slug(self, value: str) -> str:
        instance = getattr(self, "instance", None)
        if Organization.objects.filter(slug=value).exclude(pk=getattr(instance, "pk", None)).exists():
            raise serializers.ValidationError("An organization with this slug already exists.")
        return value


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["id", "user", "user_email", "user_name", "organization", "role", "joined_at"]
        read_only_fields = ["id", "joined_at"]

    def get_user_name(self, obj: Membership) -> str:
        return obj.user.get_full_name() or obj.user.username


class InvitationSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.CharField(source="invited_by.email", read_only=True)

    class Meta:
        model = Invitation
        fields = [
            "id", "organization", "email", "role", "invited_by",
            "invited_by_email", "status", "created_at", "expires_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=Membership.OrgRole.choices,
        default=Membership.OrgRole.MEMBER,
    )
