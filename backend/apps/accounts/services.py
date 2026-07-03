from __future__ import annotations

import logging
import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Profile

logger = logging.getLogger(__name__)
User = get_user_model()


class AccountService:
    """Service for user and profile management operations."""

    @staticmethod
    @transaction.atomic
    def create_user(
        username: str,
        email: str,
        password: str,
        *,
        role: str = User.Role.VIEWER,
        **extra_fields: Any,
    ) -> User:
        """Create a new user with profile."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            **extra_fields,
        )
        Profile.objects.create(user=user)
        logger.info("Created user %s with role %s", username, role)
        return user

    @staticmethod
    def get_user(user_id: uuid.UUID) -> User | None:
        """Retrieve a user by ID."""
        try:
            return User.objects.select_related("profile").get(pk=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_profile(user_id: uuid.UUID) -> Profile | None:
        """Retrieve a user profile by user ID."""
        try:
            return Profile.objects.select_related("user").get(user_id=user_id)
        except Profile.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def update_profile(
        user_id: uuid.UUID,
        *,
        phone: str | None = None,
        department: str | None = None,
        job_title: str | None = None,
        bio: str | None = None,
        timezone: str | None = None,
    ) -> Profile | None:
        """Update user profile fields."""
        try:
            profile = Profile.objects.get(user_id=user_id)
        except Profile.DoesNotExist:
            return None

        if phone is not None:
            profile.phone = phone
        if department is not None:
            profile.department = department
        if job_title is not None:
            profile.job_title = job_title
        if bio is not None:
            profile.bio = bio
        if timezone is not None:
            profile.timezone = timezone

        profile.save()
        return profile

    @staticmethod
    def approve_user(user_id: uuid.UUID) -> User | None:
        """Approve a user account."""
        try:
            user = User.objects.get(pk=user_id)
            user.is_approved = True
            user.save(update_fields=["is_approved"])
            return user
        except User.DoesNotExist:
            return None

    @staticmethod
    def set_user_role(user_id: uuid.UUID, role: str) -> User | None:
        """Set a user's role."""
        if role not in dict(User.Role.choices):
            raise ValueError(f"Invalid role: {role}")
        try:
            user = User.objects.get(pk=user_id)
            user.role = role
            user.save(update_fields=["role"])
            return user
        except User.DoesNotExist:
            return None

    @staticmethod
    def list_users(
        *,
        role: str | None = None,
        is_approved: bool | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """List users with optional filtering."""
        qs = User.objects.select_related("profile").all()
        if role is not None:
            qs = qs.filter(role=role)
        if is_approved is not None:
            qs = qs.filter(is_approved=is_approved)
        return list(qs.order_by("-date_joined")[offset:offset + limit])
