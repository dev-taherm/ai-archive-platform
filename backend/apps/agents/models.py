from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Agent(models.Model):
    """Represents an edge agent running on a user's machine."""

    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        SYNCING = "syncing", "Syncing"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agents",
    )
    agent_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Human-readable agent identifier (e.g. laptop-01).",
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OFFLINE,
    )

    # Configuration
    sync_interval_minutes = models.IntegerField(default=30)
    max_file_size_mb = models.IntegerField(default=100)
    push_original_files = models.BooleanField(
        default=False,
        help_text="If true, agent pushes original file bytes. Otherwise only metadata.",
    )

    # Platform info
    platform = models.CharField(max_length=50, blank=True, default="")
    hostname = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    agent_version = models.CharField(max_length=20, blank=True, default="")
    capabilities = models.JSONField(
        default=list,
        blank=True,
        help_text='List of agent capabilities, e.g. ["ocr", "parsing", "embedding"].',
    )

    # Tracking
    last_seen = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    files_count = models.IntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)

    # Auth
    api_key = models.OneToOneField(
        "apikeys.ApiKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agents_agent"
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
        ordering = ["-last_seen"]
        indexes = [
            models.Index(fields=["user"], name="idx_agent_user"),
            models.Index(fields=["status"], name="idx_agent_status"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.agent_id})"


class AgentFolder(models.Model):
    """A folder on the agent machine that is being monitored."""

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="folders")
    local_path = models.CharField(max_length=1024)
    label = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    file_count = models.IntegerField(default=0)

    class Meta:
        db_table = "agents_folder"
        verbose_name = "Agent Folder"
        verbose_name_plural = "Agent Folders"
        unique_together = ["agent", "local_path"]

    def __str__(self) -> str:
        return f"{self.label or self.local_path} @ {self.agent.name}"


class AgentCommand(models.Model):
    """A command pushed to an agent, fetched on next heartbeat."""

    class CommandType(models.TextChoices):
        SYNC = "sync", "Sync"
        SCAN = "scan", "Scan"
        PROCESS = "process", "Process"
        CONFIG_UPDATE = "config_update", "Config Update"
        SHUTDOWN = "shutdown", "Shutdown"
        UPDATE = "update", "Update Agent"
        RESTART = "restart", "Restart Agent"
        START_SCAN = "start_scan", "Start Continuous Scan"
        STOP_SCAN = "stop_scan", "Stop Continuous Scan"

    class CommandStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="commands")
    command_type = models.CharField(max_length=30, choices=CommandType.choices)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=CommandStatus.choices,
        default=CommandStatus.PENDING,
    )
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "agents_command"
        verbose_name = "Agent Command"
        verbose_name_plural = "Agent Commands"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.command_type} -> {self.agent.name} [{self.status}]"
