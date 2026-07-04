from __future__ import annotations

import uuid

from django.db import models


class AITask(models.Model):
    """Tracks AI processing tasks for audit and monitoring."""

    class TaskType(models.TextChoices):
        CLASSIFY = "classify", "Classify"
        EXTRACT = "extract", "Extract"
        SUMMARIZE = "summarize", "Summarize"
        EMBED = "embed", "Embed"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    document_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    input_preview = models.TextField(blank=True, default="")
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    processing_time_ms = models.FloatField(null=True, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    model_used = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_aitask"
        verbose_name = "AI Task"
        verbose_name_plural = "AI Tasks"
        indexes = [
            models.Index(fields=["task_type", "status"], name="idx_aitask_type_status"),
            models.Index(fields=["document_id"], name="idx_aitask_document"),
            models.Index(fields=["created_at"], name="idx_aitask_created"),
        ]

    def __str__(self) -> str:
        return f"AITask({self.task_type}) [{self.status}]"


class Embedding(models.Model):
    """Django model for storing embedding vectors with metadata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vector_id = models.CharField(max_length=255, unique=True, db_index=True)
    embedding = models.JSONField(default=list)
    metadata = models.JSONField(default=dict, blank=True)
    document_id = models.UUIDField(null=True, blank=True, db_index=True)
    file_id = models.UUIDField(null=True, blank=True, db_index=True)
    chunk_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "embeddings"
        verbose_name = "Embedding"
        verbose_name_plural = "Embeddings"
        indexes = [
            models.Index(fields=["document_id"], name="idx_embedding_document"),
            models.Index(fields=["file_id"], name="idx_embedding_file"),
        ]

    def __str__(self) -> str:
        return f"Embedding({self.vector_id})"


class ProviderConfig(models.Model):
    """Stores LLM/Embedding provider configurations in the database."""

    class ProviderType(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        GOOGLE = "google", "Google Gemini"
        OLLAMA = "ollama", "Ollama (Local)"

    class Capability(models.TextChoices):
        LLM = "llm", "LLM"
        EMBEDDING = "embedding", "Embedding"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    provider_type = models.CharField(max_length=20, choices=ProviderType.choices)
    capabilities = models.JSONField(default=list)  # ["llm", "embedding"]
    api_key = models.CharField(max_length=500, blank=True, default="")
    base_url = models.CharField(max_length=500, blank=True, default="")
    model_name = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True)  # Extra config options
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_providerconfig"
        verbose_name = "Provider Config"
        verbose_name_plural = "Provider Configs"
        ordering = ["-is_default", "name"]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.provider_type})"
