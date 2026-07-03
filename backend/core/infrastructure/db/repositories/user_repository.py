from __future__ import annotations

import uuid
from typing import Any, Sequence

from django.db.models import QuerySet

from core.application.interfaces.repositories import UserRepository
from core.domain.common.exceptions import EntityNotFound


class DjangoUserRepository(UserRepository):
    """Django ORM implementation of UserRepository ABC.

    References apps.accounts.models.User as the canonical user model.
    """

    def __init__(self) -> None:
        from apps.accounts.models import User
        self._model = User

    def _qs(self) -> QuerySet:
        return self._model.objects.all()

    def _to_dict(self, user: Any) -> dict[str, Any]:
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_approved": user.is_approved,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "last_login_ip": getattr(user, "last_login_ip", None),
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

    async def get_by_id(self, user_id: uuid.UUID) -> dict[str, Any] | None:
        try:
            user = await self._qs().aget(id=user_id)
            return self._to_dict(user)
        except self._model.DoesNotExist:
            return None

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        try:
            user = await self._qs().aget(email__iexact=email)
            return self._to_dict(user)
        except self._model.DoesNotExist:
            return None

    async def save(self, user: dict[str, Any]) -> dict[str, Any]:
        user_id = user.get("id")
        if user_id:
            try:
                obj = await self._qs().aget(id=user_id)
                for field in (
                    "email", "username", "first_name", "last_name",
                    "role", "is_active", "is_approved", "is_staff",
                    "is_superuser",
                ):
                    if field in user:
                        setattr(obj, field, user[field])
                if "password" in user and user["password"]:
                    obj.set_password(user["password"])
                obj.save()
                return self._to_dict(obj)
            except self._model.DoesNotExist:
                pass

        obj = self._model.objects.create_user(
            email=user.get("email", ""),
            password=user.get("password"),
            username=user.get("username", ""),
            first_name=user.get("first_name", ""),
            last_name=user.get("last_name", ""),
            role=user.get("role", self._model.Role.VIEWER),
            is_active=user.get("is_active", True),
            is_approved=user.get("is_approved", False),
        )
        return self._to_dict(obj)

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        qs = self._qs().order_by("-date_joined")[offset : offset + limit]
        return [self._to_dict(user) async for user in qs]
