from __future__ import annotations

import base64
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.agents.models import Agent, AgentCommand, AgentFolder
from apps.agents.serializers import (
    AgentCommandSerializer,
    AgentCreateSerializer,
    AgentFolderSerializer,
    AgentHeartbeatSerializer,
    AgentSerializer,
    AgentSyncSerializer,
)

logger = logging.getLogger(__name__)


class IsAgentOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class AgentViewSet(viewsets.ModelViewSet):
    """CRUD for edge agents. Also provides heartbeat, sync, and command endpoints."""

    permission_classes = [permissions.IsAuthenticated, IsAgentOwner]
    lookup_field = "agent_id"

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user).prefetch_related(
            "folders", "commands"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return AgentCreateSerializer
        return AgentSerializer

    def perform_create(self, serializer):
        agent = serializer.save(user=self.request.user)

        # Auto-create an API key for the agent
        from apps.apikeys.models import ApiKey

        api_key_instance, raw_key = ApiKey.create_key(
            self.request.user, name=f"agent:{agent.agent_id}"
        )
        agent.api_key = api_key_instance
        agent.save(update_fields=["api_key"])

        # Store the raw key in context so serializer can include it
        self._raw_agent_key = raw_key

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        agent = serializer.instance
        raw_key = getattr(self, "_raw_agent_key", None)

        # Return agent data with the API key (only shown once)
        response_data = AgentSerializer(agent).data
        response_data["api_key"] = raw_key
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="heartbeat")
    def heartbeat(self, request, agent_id=None):
        """Agent reports its current status."""
        agent = self.get_object()
        serializer = AgentHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        now = timezone.now()
        agent.status = data["status"]
        agent.platform = data.get("platform", agent.platform)
        agent.hostname = data.get("hostname", agent.hostname)
        agent.ip_address = data.get("ip_address", agent.ip_address)
        agent.agent_version = data.get("agent_version", agent.agent_version)
        agent.files_count = data.get("files_count", agent.files_count)
        agent.total_size_bytes = data.get("total_size_bytes", agent.total_size_bytes)
        agent.last_seen = now
        agent.save(update_fields=[
            "status", "platform", "hostname", "ip_address",
            "agent_version", "files_count", "total_size_bytes", "last_seen",
        ])

        # Sync folders
        folders_monitored = data.get("folders_monitored", [])
        if folders_monitored:
            existing = {f.local_path: f for f in agent.folders.all()}
            for path in folders_monitored:
                if path not in existing:
                    AgentFolder.objects.create(agent=agent, local_path=path)

        # Return pending commands + config
        pending = list(
            agent.commands.filter(status="pending").order_by("created_at")[:20]
        )
        for cmd in pending:
            cmd.status = "delivered"
            cmd.save(update_fields=["status"])

        return Response({
            "status": "ok",
            "sync_interval_minutes": agent.sync_interval_minutes,
            "pending_commands": AgentCommandSerializer(pending, many=True).data,
            "config": {
                "push_original_files": agent.push_original_files,
                "max_file_size_mb": agent.max_file_size_mb,
            },
        })

    @action(detail=True, methods=["get", "post"], url_path="commands")
    def commands(self, request, agent_id=None):
        """Fetch pending commands or report command result."""
        agent = self.get_object()

        if request.method == "GET":
            pending = list(
                agent.commands.filter(status="pending").order_by("created_at")[:20]
            )
            for cmd in pending:
                cmd.status = "delivered"
                cmd.save(update_fields=["status"])
            return Response(AgentCommandSerializer(pending, many=True).data)

        # POST — report command result
        cmd_id = request.data.get("command_id")
        cmd_status = request.data.get("status", "completed")
        result = request.data.get("result")

        try:
            cmd = AgentCommand.objects.get(id=cmd_id, agent=agent)
        except AgentCommand.DoesNotExist:
            return Response(
                {"detail": "Command not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        cmd.status = cmd_status
        cmd.result = result
        cmd.executed_at = timezone.now()
        cmd.save(update_fields=["status", "result", "executed_at"])
        return Response({"status": "ok"})

    @action(detail=True, methods=["post"], url_path="commands/create")
    def create_command(self, request, agent_id=None):
        """Push a new command to an agent."""
        agent = self.get_object()
        command_type = request.data.get("command_type")
        payload = request.data.get("payload", {})

        if not command_type:
            return Response(
                {"detail": "command_type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cmd = AgentCommand.objects.create(
            agent=agent,
            command_type=command_type,
            payload=payload,
        )
        return Response(
            AgentCommandSerializer(cmd).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, agent_id=None):
        """Receive file metadata and optional original files from agent."""
        agent = self.get_object()
        serializer = AgentSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        files_data = data["files"]
        original_files = data.get("original_files", {})
        accepted = 0
        rejected = 0
        errors = []

        from apps.files.models import FileRecord

        with transaction.atomic():
            for file_data in files_data:
                try:
                    local_path = file_data["local_path"]
                    file_hash = file_data["file_hash"]

                    # Create or update FileRecord
                    fr, created = FileRecord.objects.update_or_create(
                        content_hash=file_hash,
                        defaults={
                            "path": local_path,
                            "mime_type": file_data.get("mime_type", ""),
                            "size_bytes": file_data.get("file_size", 0),
                            "status": "completed",
                            "source": FileRecord.Source.AGENT,
                            "agent": agent,
                            "tags": file_data.get("metadata", {}).get("tags", []),
                            "metadata": {
                                **file_data.get("metadata", {}),
                                "agent_id": str(agent.agent_id),
                                "extracted_text": file_data.get("extracted_text", ""),
                                "markdown": file_data.get("markdown", ""),
                                "classification": file_data.get("classification", {}),
                                "entities": file_data.get("entities", []),
                                "summary": file_data.get("summary", ""),
                                "chunk_count": file_data.get("chunk_count", 0),
                                "ocr_used": file_data.get("ocr_used", False),
                            },
                        },
                    )

                    # Store embeddings if provided
                    embeddings = file_data.get("embeddings", [])
                    if embeddings:
                        from apps.ai.models import Embedding

                        emb_id = f"{fr.id}_chunk_0"
                        Embedding.objects.update_or_create(
                            vector_id=emb_id,
                            defaults={
                                "embedding": embeddings,
                                "document_id": str(fr.id),
                                "file_id": str(fr.id),
                                "chunk_index": 0,
                            },
                        )

                    # Save original file if requested and provided
                    if local_path in original_files:
                        raw_b64 = original_files[local_path]
                        file_bytes = base64.b64decode(raw_b64)
                        from core.infrastructure.storage.local import LocalStorage

                        storage = LocalStorage()
                        storage.save(file_bytes, f"agent/{agent.agent_id}/{local_path}")

                    accepted += 1
                except Exception as e:
                    rejected += 1
                    errors.append({"file": file_data.get("local_path", "?"), "error": str(e)})
                    logger.warning("Sync error for %s: %s", file_data.get("local_path"), e)

            agent.last_sync_at = timezone.now()
            agent.save(update_fields=["last_sync_at"])

        # Return pending commands
        pending = list(
            agent.commands.filter(status="pending").order_by("created_at")[:20]
        )
        for cmd in pending:
            cmd.status = "delivered"
            cmd.save(update_fields=["status"])

        return Response({
            "status": "ok",
            "accepted": accepted,
            "rejected": rejected,
            "errors": errors,
            "pending_commands": AgentCommandSerializer(pending, many=True).data,
        })
