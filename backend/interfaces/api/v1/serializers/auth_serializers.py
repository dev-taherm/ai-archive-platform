from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class LoginSerializer(TokenObtainPairSerializer):
    """JWT login serializer extending SimpleJWT's token pair."""

    email = serializers.EmailField()

    default_error_messages = {
        "invalid_credentials": "Invalid email or password.",
        "inactive_user": "Account is disabled.",
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False
        self.fields["username"].allow_blank = True

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["current_org_id"] = str(user.current_organization_id) if user.current_organization_id else None
        return token

    def validate_email(self, value: str) -> str:
        try:
            user = User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                self.error_messages["invalid_credentials"]
            )
        self.user = user
        return value

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email", "")
        password = attrs.get("password", "")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"email": [self.error_messages["invalid_credentials"]]}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {"password": [self.error_messages["invalid_credentials"]]}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": [self.error_messages["inactive_user"]]}
            )

        attrs["username"] = user.username
        tokens = super().validate(attrs)
        tokens["user"] = user
        return tokens


class RegisterSerializer(serializers.ModelSerializer):
    """User registration serializer with password validation."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    invitation_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "invitation_token",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_invitation_token(self, value: str) -> str:
        if not value:
            return value
        from apps.organizations.models import Invitation

        try:
            invitation = Invitation.objects.get(
                token=value,
                status=Invitation.Status.PENDING,
            )
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invitation token.")

        if invitation.expires_at < timezone.now():
            raise serializers.ValidationError("This invitation has expired.")

        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data: dict) -> User:
        invitation_token = validated_data.pop("invitation_token", None)
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # If registering via invitation, accept it and add to org
        if invitation_token:
            from apps.organizations.services import OrgService

            OrgService.accept_invitation(invitation_token, user)

        return user


class UserSerializer(serializers.ModelSerializer):
    """Read-only user serializer for profile and admin views."""

    organization_name = serializers.CharField(
        source="current_organization.name", read_only=True, default=None
    )
    organization_slug = serializers.CharField(
        source="current_organization.slug", read_only=True, default=None
    )
    org_role = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "current_organization",
            "organization_name",
            "organization_slug",
            "org_role",
            "organizations",
        ]
        read_only_fields = ["id", "email", "date_joined"]

    def get_org_role(self, obj) -> str | None:
        """Return the user's role in their current organization."""
        if not obj.current_organization_id:
            return None
        from apps.organizations.models import Membership

        try:
            membership = Membership.objects.get(user=obj, organization=obj.current_organization)
            return membership.role
        except Membership.DoesNotExist:
            return None

    def get_organizations(self, obj) -> list[dict]:
        """Return all organizations the user belongs to."""
        from apps.organizations.models import Membership

        memberships = Membership.objects.filter(user=obj).select_related("organization")
        return [
            {
                "id": str(m.organization_id),
                "name": m.organization.name,
                "slug": m.organization.slug,
                "role": m.role,
            }
            for m in memberships
        ]


class TokenRefreshSerializer(serializers.Serializer):
    """Token refresh serializer with response serialization."""

    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)
