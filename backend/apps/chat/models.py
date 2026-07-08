from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """A chat conversation session between a user and the AI assistant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    title = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_session"
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"
        indexes = [
            models.Index(fields=["user", "created_at"], name="idx_chatsession_user_time"),
        ]

    def __str__(self) -> str:
        return f"ChatSession({self.id}) — {self.title}"


class ChatMessage(models.Model):
    """A single message within a chat session."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    model_used = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["session", "created_at"], name="idx_chatmsg_session_time"),
        ]

    def __str__(self) -> str:
        return f"[{self.role}] {self.content[:60]}"
