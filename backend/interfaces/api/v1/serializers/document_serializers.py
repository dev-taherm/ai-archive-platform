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
    document_index = serializers.IntegerField(read_only=True)
    page_start = serializers.IntegerField(read_only=True, allow_null=True)
    page_end = serializers.IntegerField(read_only=True, allow_null=True)
    total_documents_for_file = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_path = serializers.SerializerMethodField()
    file_mime_type = serializers.SerializerMethodField()
    doc_type = serializers.CharField(read_only=True)
    processing_status = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True, default="")
    author = serializers.CharField(read_only=True, default="")
    subject = serializers.CharField(read_only=True, default="")
    language = serializers.CharField(read_only=True, default="unknown")
    word_count = serializers.IntegerField(read_only=True, default=0)
    page_count = serializers.IntegerField(read_only=True, default=0)
    chunk_count = serializers.IntegerField(read_only=True, default=0)
    classification_confidence = serializers.FloatField(
        read_only=True, allow_null=True
    )
    tags = serializers.ListField(
        child=serializers.CharField(), read_only=True, default=list
    )
    extracted_text_preview = serializers.CharField(read_only=True, default="")
    summary = serializers.CharField(read_only=True, default="")
    entities = serializers.SerializerMethodField()
    error_message = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_file_name(self, obj):
        """Look up the original filename from the FileRecord."""
        file_id = getattr(obj, "file_id", None)
        if not file_id:
            return ""
        try:
            from apps.files.models import FileRecord
            fr = FileRecord.objects.get(id=file_id)
            import os
            return os.path.basename(fr.path)
        except Exception:
            return ""

    def get_file_path(self, obj):
        """Look up the full file path from the FileRecord."""
        file_id = getattr(obj, "file_id", None)
        if not file_id:
            return ""
        try:
            from apps.files.models import FileRecord
            fr = FileRecord.objects.get(id=file_id)
            return fr.path
        except Exception:
            return ""

    def get_file_mime_type(self, obj):
        """Look up the MIME type from the FileRecord."""
        file_id = getattr(obj, "file_id", None)
        if not file_id:
            return ""
        try:
            from apps.files.models import FileRecord
            fr = FileRecord.objects.get(id=file_id)
            return fr.mime_type
        except Exception:
            return ""

    def get_total_documents_for_file(self, obj):
        """Return the number of documents that share the same file_id."""
        from apps.documents.models import Document as DocModel
        return DocModel.objects.filter(file_id=obj.file_id).count()

    def get_entities(self, obj):
        """Return extracted entities for this document."""
        entities = obj.entities.all() if hasattr(obj, "entities") else []
        return ExtractedEntitySerializer(entities, many=True).data


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


class ExtractedEntitySerializer(serializers.Serializer):
    """Serializer for an extracted named entity."""

    id = serializers.UUIDField(read_only=True)
    entity_type = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    context = serializers.CharField(read_only=True, default="")
    confidence = serializers.FloatField(read_only=True, allow_null=True)
    source = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


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


class DocumentUpdateSerializer(serializers.Serializer):
    """Serializer for partial document updates (PATCH)."""

    title = serializers.CharField(max_length=500, required=False)
    author = serializers.CharField(max_length=255, required=False)
    subject = serializers.CharField(max_length=500, required=False)
    doc_type = serializers.ChoiceField(
        choices=[
            "invoice", "contract", "report", "letter",
            "memo", "receipt", "unknown",
        ],
        required=False,
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
    )
