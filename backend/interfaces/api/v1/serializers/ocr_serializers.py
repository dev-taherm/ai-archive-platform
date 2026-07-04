from __future__ import annotations

from rest_framework import serializers


class OcrJobSerializer(serializers.Serializer):
    """Serializer for OCR job representation."""

    id = serializers.UUIDField(read_only=True)
    file_id = serializers.UUIDField(read_only=True)
    file_name = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    language = serializers.CharField(read_only=True)
    confidence = serializers.FloatField(read_only=True, allow_null=True)
    text_length = serializers.SerializerMethodField()
    error_message = serializers.CharField(read_only=True, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)

    def get_file_name(self, obj) -> str:
        file_names = self.context.get("file_names", {})
        return file_names.get(str(obj.file_id), str(obj.file_id))

    def get_text_length(self, obj) -> int:
        return len(obj.extracted_text) if obj.extracted_text else 0


class OcrJobCreateSerializer(serializers.Serializer):
    """Serializer for creating an OCR job."""

    file_id = serializers.UUIDField()
    source_type = serializers.ChoiceField(
        choices=[("image", "Image"), ("pdf", "PDF")],
        default="image",
    )
    language = serializers.CharField(max_length=10, default="eng", required=False)
