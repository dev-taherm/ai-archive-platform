from __future__ import annotations

from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for a chat message."""

    id = serializers.UUIDField(read_only=True)
    session_id = serializers.UUIDField(read_only=True)
    role = serializers.ChoiceField(
        choices=["user", "assistant", "system"], read_only=True
    )
    content = serializers.CharField(read_only=True)
    sources = serializers.ListField(
        child=serializers.DictField(), read_only=True, default=list
    )
    tool_calls = serializers.ListField(
        child=serializers.DictField(), read_only=True, default=list
    )
    metadata = serializers.DictField(read_only=True, default=dict)
    tokens_used = serializers.IntegerField(read_only=True, default=0)
    model_used = serializers.CharField(read_only=True, default="")
    created_at = serializers.DateTimeField(read_only=True)


class ChatSessionSerializer(serializers.Serializer):
    """Serializer for a chat session."""

    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for a chat response wrapping an assistant message."""

    message = ChatMessageSerializer(read_only=True)
    session_id = serializers.UUIDField(read_only=True)
    references = ChatMessageSerializer(many=True, read_only=True, default=list)
    processing_time_ms = serializers.FloatField(read_only=True, default=0.0)
    tokens_used = serializers.IntegerField(read_only=True, default=0)


class ChatSendMessageSerializer(serializers.Serializer):
    """Serializer for sending a chat message."""

    message = serializers.CharField(
        min_length=1,
        max_length=10000,
        help_text="The user message to send.",
        style={"base_template": "textarea.html"},
    )

    def validate_message(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Message cannot be empty.")
        return value


class ChatSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating a new chat session."""

    title = serializers.CharField(
        max_length=256,
        required=False,
        default="",
        help_text="Optional session title.",
    )
