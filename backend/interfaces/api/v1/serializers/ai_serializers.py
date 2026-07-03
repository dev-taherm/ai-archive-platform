from __future__ import annotations

from rest_framework import serializers


class ClassificationSerializer(serializers.Serializer):
    """Serializer for AI classification requests and results."""

    text = serializers.CharField(
        max_length=10000,
        min_length=1,
        help_text="Text content to classify.",
        style={"base_template": "textarea.html"},
    )
    categories = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=None,
        allow_null=True,
        help_text="Optional target categories.",
    )
    system_prompt = serializers.CharField(
        required=False,
        default=None,
        allow_null=True,
        max_length=5000,
        help_text="Optional system prompt override.",
    )

    # Response fields
    predicted_label = serializers.CharField(read_only=True)
    confidence = serializers.FloatField(read_only=True)
    all_labels = serializers.DictField(
        child=serializers.FloatField(), read_only=True
    )
    model_used = serializers.CharField(read_only=True)
    classified_at = serializers.DateTimeField(read_only=True)


class ExtractionSerializer(serializers.Serializer):
    """Serializer for AI data extraction requests and results."""

    text = serializers.CharField(
        max_length=10000,
        min_length=1,
        help_text="Text content to extract fields from.",
        style={"base_template": "textarea.html"},
    )
    fields = serializers.ListField(
        child=serializers.CharField(max_length=100),
        min_length=1,
        help_text="Fields to extract (e.g. ['title', 'author', 'date']).",
    )
    system_prompt = serializers.CharField(
        required=False,
        default=None,
        allow_null=True,
        max_length=5000,
        help_text="Optional system prompt override.",
    )

    # Response fields
    extracted_data = serializers.DictField(read_only=True)
    model_used = serializers.CharField(read_only=True)


class SummarizeSerializer(serializers.Serializer):
    """Serializer for AI summarization requests."""

    text = serializers.CharField(
        max_length=50000,
        min_length=1,
        help_text="Text content to summarize.",
        style={"base_template": "textarea.html"},
    )
    max_tokens = serializers.IntegerField(
        default=500,
        min_value=50,
        max_value=4096,
        help_text="Maximum tokens in the summary.",
    )
    system_prompt = serializers.CharField(
        required=False,
        default=None,
        allow_null=True,
        max_length=5000,
        help_text="Optional system prompt override.",
    )

    # Response fields
    summary = serializers.CharField(read_only=True)


class AIProviderSerializer(serializers.Serializer):
    """Serializer for AI provider configuration."""

    name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    models = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    capabilities = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )


class AIProviderListSerializer(serializers.Serializer):
    """Serializer for list of AI providers."""

    providers = AIProviderSerializer(many=True, read_only=True)
