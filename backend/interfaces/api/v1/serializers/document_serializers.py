from __future__ import annotations

from rest_framework import serializers


class DocumentMetadataSerializer(serializers.Serializer):
    """Serializer for document metadata."""

    title = serializers.CharField(read_only=True, default="")
    author = serializers.CharField(read_only=True, default="")
    subject = serializers.CharField(read_only=True, default="")
    keywords = serializers.ListField(
        child=serializers.CharField(), read_only=True, default=list
    )
    creation_date = serializers.CharField(read_only=True, default="")
    modification_date = serializers.CharField(read_only=True, default="")
    page_count = serializers.IntegerField(read_only=True, default=0)
    word_count = serializers.IntegerField(read_only=True, default=0)
    char_count = serializers.IntegerField(read_only=True, default=0)
    language = serializers.CharField(read_only=True, default="unknown")
    extra = serializers.DictField(read_only=True, default=dict)


class DocumentSerializer(serializers.Serializer):
    """Serializer for document representation."""

    id = serializers.UUIDField(read_only=True)
    file_id = serializers.UUIDField(read_only=True)
    doc_type = serializers.CharField(read_only=True)
    processing_status = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True, source="metadata.title", default="")
    author = serializers.CharField(read_only=True, source="metadata.author", default="")
    subject = serializers.CharField(
        read_only=True, source="metadata.subject", default=""
    )
    language = serializers.CharField(
        read_only=True, source="metadata.language", default="unknown"
    )
    word_count = serializers.IntegerField(read_only=True, default=0)
    page_count = serializers.IntegerField(
        read_only=True, source="metadata.page_count", default=0
    )
    chunk_count = serializers.IntegerField(read_only=True, default=0)
    classification_confidence = serializers.FloatField(
        read_only=True, allow_null=True
    )
    tags = serializers.ListField(
        child=serializers.CharField(), read_only=True, default=list
    )
    extracted_text_preview = serializers.CharField(read_only=True, default="")
    error_message = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class DocumentChunkSerializer(serializers.Serializer):
    """Serializer for document chunk representation."""

    id = serializers.UUIDField(read_only=True)
    document_id = serializers.UUIDField(read_only=True)
    chunk_index = serializers.IntegerField(read_only=True)
    content = serializers.CharField(read_only=True)
    start_offset = serializers.IntegerField(read_only=True)
    end_offset = serializers.IntegerField(read_only=True)
    embedding_id = serializers.CharField(read_only=True, allow_null=True)
    metadata = serializers.DictField(read_only=True, default=dict)


class DocumentProcessSerializer(serializers.Serializer):
    """Serializer for document processing requests."""

    file_id = serializers.UUIDField(
        help_text="UUID of the file to process as a document."
    )


class DocumentClassifySerializer(serializers.Serializer):
    """Serializer for document classification requests."""

    categories = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=None,
        allow_null=True,
        help_text="Optional list of target categories.",
    )


class DocumentExtractSerializer(serializers.Serializer):
    """Serializer for document metadata extraction requests."""

    fields = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=None,
        allow_null=True,
        help_text="Optional list of fields to extract.",
    )
