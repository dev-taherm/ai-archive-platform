from __future__ import annotations

from rest_framework import serializers


class SearchFiltersSerializer(serializers.Serializer):
    """Serializer for search filter parameters."""

    doc_types = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    languages = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    date_from = serializers.DateTimeField(required=False, allow_null=True, default=None)
    date_to = serializers.DateTimeField(required=False, allow_null=True, default=None)
    min_score = serializers.FloatField(required=False, default=0.0, min_value=0.0)
    file_extensions = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    exclude_duplicates = serializers.BooleanField(required=False, default=True)


class SearchQuerySerializer(serializers.Serializer):
    """Serializer for search query requests."""

    query = serializers.CharField(
        max_length=2000,
        min_length=1,
        help_text="The search query text.",
    )
    search_type = serializers.ChoiceField(
        choices=["hybrid", "semantic", "keyword"],
        default="hybrid",
        help_text="Search strategy to use.",
    )
    max_results = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text="Maximum number of results to return.",
    )
    offset = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Offset for pagination.",
    )
    filters = SearchFiltersSerializer(required=False, default=dict)
    include_chunks = serializers.BooleanField(default=False)

    def validate_query(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Search query cannot be empty.")
        return value


class SearchResultSerializer(serializers.Serializer):
    """Serializer for a single search result."""

    document_id = serializers.UUIDField()
    file_id = serializers.UUIDField()
    title = serializers.CharField()
    snippet = serializers.CharField()
    score = serializers.FloatField()
    rank = serializers.IntegerField()
    doc_type = serializers.CharField(default="unknown")
    language = serializers.CharField(default="unknown")
    match_source = serializers.CharField(default="")
    highlights = serializers.ListField(
        child=serializers.CharField(), default=list
    )
    metadata = serializers.DictField(default=dict)


class SearchResponseSerializer(serializers.Serializer):
    """Serializer for paginated search response."""

    query = serializers.CharField()
    results = SearchResultSerializer(many=True, read_only=True)
    total_count = serializers.IntegerField()
    search_time_ms = serializers.FloatField()
    search_type = serializers.CharField(default="hybrid")
    applied_filters = SearchFiltersSerializer(read_only=True)
