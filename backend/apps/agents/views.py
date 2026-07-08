from __future__ import annotations

import io
import json
import logging
import uuid
import zipfile
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from apps.agents.models import Agent, AgentCommand, AgentFolder
from apps.agents.serializers import (
    AgentCommandSerializer,
    AgentCreateSerializer,
    AgentFolderCreateSerializer,
    AgentFolderSerializer,
    AgentFolderUpdateSerializer,
    AgentHeartbeatSerializer,
    AgentSerializer,
    AgentSetupSerializer,
    AgentSyncSerializer,
    FileMoveFolderSerializer,
    FileMoveSerializer,
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

    @action(detail=False, methods=["post"], url_path="setup")
    def setup(self, request):
        """Quick-setup endpoint: returns a JWT token for the download package.

        The edge agent binary auto-registers on first run using the JWT token.
        No agent is created server-side — each device registers itself.
        """
        # Generate a short-lived access token for the current user
        refresh = RefreshToken.for_user(request.user)
        access_token = str(refresh.access_token)

        server_url = request.build_absolute_uri("/").rstrip("/")

        return Response({
            "jwt_token": access_token,
            "server_url": server_url,
            "download_url": "/agents/download-package",
            "existing_agents_count": Agent.objects.filter(user=request.user).count(),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="auto-register")
    def auto_register(self, request):
        """Smart registration: reuses existing agent if same user+hostname, otherwise creates new.

        Auth: JWT (the user's login token).
        Body: { hostname, platform, agent_version?, name? }
        Returns: { agent_id, api_key, is_new }
        """
        logger.debug("auto-register request.data: %s", dict(request.data))
        hostname = request.data.get("hostname", "").strip()
        platform_name = request.data.get("platform", "").strip()
        agent_version = request.data.get("agent_version", "")
        agent_name = request.data.get("name", "")

        if not hostname:
            return Response(
                {"detail": "hostname is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if this user already has an agent on this hostname
        existing = Agent.objects.filter(
            user=request.user, hostname=hostname
        ).first()

        from apps.apikeys.models import ApiKey

        if existing:
            # Reuse: deactivate old key, generate new one
            if existing.api_key:
                existing.api_key.is_active = False
                existing.api_key.save(update_fields=["is_active"])

            api_key_instance, raw_key = ApiKey.create_key(
                request.user, name=f"agent:{existing.agent_id}"
            )
            existing.api_key = api_key_instance
            existing.platform = platform_name or existing.platform
            existing.hostname = hostname or existing.hostname
            existing.agent_version = agent_version or existing.agent_version
            existing.last_seen = timezone.now()
            existing.save(update_fields=[
                "api_key", "platform", "hostname", "agent_version", "last_seen",
            ])

            logger.info("Reused agent %s for hostname=%s", existing.agent_id, hostname)
            return Response({
                "agent_id": existing.agent_id,
                "api_key": raw_key,
                "is_new": False,
            }, status=status.HTTP_200_OK)

        # New agent
        import secrets
        agent_id = secrets.token_hex(8)  # 16-char hex ID
        # Ensure unique
        while Agent.objects.filter(agent_id=agent_id).exists():
            agent_id = secrets.token_hex(8)

        agent = Agent.objects.create(
            user=request.user,
            agent_id=agent_id,
            name=agent_name or f"Agent on {hostname}",
            hostname=hostname,
            platform=platform_name,
            agent_version=agent_version,
            status=Agent.Status.OFFLINE,
        )

        api_key_instance, raw_key = ApiKey.create_key(
            request.user, name=f"agent:{agent_id}"
        )
        agent.api_key = api_key_instance
        agent.save(update_fields=["api_key"])

        logger.info("Created new agent %s for hostname=%s", agent_id, hostname)
        return Response({
            "agent_id": agent_id,
            "api_key": raw_key,
            "is_new": True,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, agent_id=None):
        """Serve a zip file with the edge-agent binary + pre-configured config.yaml + install script.

        Query params:
            os: "linux" | "darwin" | "windows" (required)
        """
        agent = self.get_object()
        os_param = request.query_params.get("os", "").lower()

        valid_os = {"linux", "darwin", "windows"}
        if os_param not in valid_os:
            return Response(
                {"detail": f"os must be one of: {', '.join(sorted(valid_os))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine binary filename
        arch = "x86_64"
        suffix = ".exe" if os_param == "windows" else ""
        binary_name = f"edge-agent-{os_param}-{arch}{suffix}"

        # Look for the binary in media/agents/binaries/
        binaries_dir = Path(settings.MEDIA_ROOT) / "agents" / "binaries"
        binary_path = binaries_dir / binary_name

        if not binary_path.exists():
            return Response(
                {"detail": f"Binary not available for {os_param}/{arch}. "
                           f"Please build it first: python edge_agent/build.py"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate config.yaml — api_key comes from the frontend (setup response)
        api_key_param = request.query_params.get("api_key", "")
        config_yaml = _generate_config_yaml(
            agent_id=agent.agent_id,
            api_key=api_key_param,
            server_url=request.build_absolute_uri("/").rstrip("/"),
        )

        # Generate install script
        if os_param == "windows":
            install_script = _generate_install_bat()
            install_name = "install.bat"
        else:
            install_script = _generate_install_sh()
            install_name = "install.sh"

        # Build zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(binary_name, binary_path.read_bytes())
            zf.writestr("config.yaml", config_yaml)
            zf.writestr(install_name, install_script)
            zf.writestr("README.txt", _generate_readme(agent.agent_id, os_param))

        zip_buffer.seek(0)
        zip_filename = f"edge-agent-{agent.agent_id}-{os_param}.zip"

        return FileResponse(
            zip_buffer,
            content_type="application/zip",
            filename=zip_filename,
        )

    @action(detail=False, methods=["get"], url_path="download-package")
    def download_package(self, request):
        """Serve a zip with edge-agent binary + config pre-filled with JWT token.

        Query params:
            os: "linux" | "darwin" | "windows" (required)
            jwt_token: JWT access token for auto-registration (required)
        """
        os_param = request.query_params.get("os", "").lower()
        jwt_token = request.query_params.get("jwt_token", "")

        valid_os = {"linux", "darwin", "windows"}
        if os_param not in valid_os:
            return Response(
                {"detail": f"os must be one of: {', '.join(sorted(valid_os))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not jwt_token:
            return Response(
                {"detail": "jwt_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        arch = "x86_64"
        suffix = ".exe" if os_param == "windows" else ""
        binary_name = f"edge-agent-{os_param}-{arch}{suffix}"

        binaries_dir = Path(settings.MEDIA_ROOT) / "agents" / "binaries"
        binary_path = binaries_dir / binary_name

        if not binary_path.exists():
            return Response(
                {"detail": f"Binary not available for {os_param}/{arch}. "
                           f"Please build it first: python edge_agent/build.py"},
                status=status.HTTP_404_NOT_FOUND,
            )

        server_url = request.build_absolute_uri("/").rstrip("/")
        config_yaml = _generate_config_yaml(
            agent_id="",
            api_key="",
            server_url=server_url,
            jwt_token=jwt_token,
        )

        if os_param == "windows":
            install_script = _generate_install_bat()
            install_name = "install.bat"
        else:
            install_script = _generate_install_sh()
            install_name = "install.sh"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(binary_name, binary_path.read_bytes())
            zf.writestr("config.yaml", config_yaml)
            zf.writestr(install_name, install_script)
            zf.writestr("README.txt", _generate_readme("auto-register", os_param))

        zip_buffer.seek(0)

        return FileResponse(
            zip_buffer,
            content_type="application/zip",
            filename="edge-agent.zip",
        )

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

    @action(detail=True, methods=["get", "post"], url_path="commands/create")
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

    @action(detail=True, methods=["get", "post"], url_path="folders")
    def folders(self, request, agent_id=None):
        """List or create folders for this agent."""
        agent = self.get_object()

        if request.method == "GET":
            return Response(AgentFolderSerializer(agent.folders.all(), many=True).data)

        # POST — create folder
        serializer = AgentFolderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        folder = AgentFolder.objects.create(
            agent=agent,
            local_path=data["local_path"],
            label=data.get("label", ""),
            is_active=data.get("is_active", True),
        )
        return Response(
            AgentFolderSerializer(folder).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch", "delete"], url_path="folders/(?P<folder_id>[0-9]+)")
    def folder_detail(self, request, agent_id=None, folder_id=None):
        """Update (move/rename) or delete a folder."""
        agent = self.get_object()

        try:
            folder = agent.folders.get(id=folder_id)
        except AgentFolder.DoesNotExist:
            return Response(
                {"detail": "Folder not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "DELETE":
            folder.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH — update folder
        serializer = AgentFolderUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        for field, value in data.items():
            setattr(folder, field, value)
        folder.save()

        return Response(AgentFolderSerializer(folder).data)

    @action(detail=True, methods=["post"], url_path="files/move")
    def move_files(self, request, agent_id=None):
        """Move files from this agent to a different agent."""
        agent = self.get_object()
        serializer = FileMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.files.models import FileRecord

        target_agent_id = data["target_agent_id"]
        try:
            target_agent = Agent.objects.get(agent_id=target_agent_id, user=request.user)
        except Agent.DoesNotExist:
            return Response(
                {"detail": "Target agent not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        file_ids = data["file_ids"]
        updated = FileRecord.objects.filter(
            id__in=file_ids, agent=agent
        ).update(agent=target_agent)

        return Response({
            "status": "ok",
            "moved": updated,
        })

    @action(detail=True, methods=["post"], url_path="files/move-folder")
    def move_files_folder(self, request, agent_id=None):
        """Move files between folders within the same agent by changing path prefix."""
        agent = self.get_object()
        serializer = FileMoveFolderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.files.models import FileRecord

        source_path = data["source_path"]
        target_path = data["target_path"]
        file_ids = data["file_ids"]

        # Update paths for matching files
        updated = 0
        files = FileRecord.objects.filter(id__in=file_ids, agent=agent)
        for f in files:
            if f.path.startswith(source_path):
                new_path = target_path + f.path[len(source_path):]
                f.path = new_path
                f.save(update_fields=["path"])
                updated += 1

        return Response({
            "status": "ok",
            "moved": updated,
        })

    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, agent_id=None):
        """Receive pre-processed file data from agent. No original files or binaries."""
        agent = self.get_object()
        serializer = AgentSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        files_data = data["files"]
        accepted = 0
        rejected = 0
        errors = []
        document_ids: list[str] = []

        from apps.files.models import FileRecord
        from apps.documents.models import Document

        with transaction.atomic():
            for file_data in files_data:
                try:
                    local_path = file_data["local_path"]
                    file_hash = file_data["file_hash"]

                    # Create or update FileRecord with pre-processed metadata
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
                                "agent_version": file_data.get("agent_version", ""),
                                "processing_version": file_data.get("processing_version", ""),
                                "parser_version": file_data.get("parser_version", ""),
                                "ocr_engine": file_data.get("ocr_engine", ""),
                                "ocr_used": file_data.get("ocr_used", False),
                                "extracted_text": file_data.get("extracted_text", ""),
                                "markdown": file_data.get("markdown", ""),
                                "content_blocks": file_data.get("content_blocks", []),
                                "tables": file_data.get("tables", []),
                                "images": file_data.get("images", []),
                            },
                        },
                    )

                    # Create Document with pre-populated fields from agent
                    doc = Document.objects.create(
                        file_id=fr.id,
                        doc_type=Document.DocType.UNKNOWN,
                        processing_status=Document.Status.PENDING,
                        title=Path(local_path).stem,
                        language=file_data.get("language", "unknown"),
                        word_count=file_data.get("word_count", 0),
                        char_count=file_data.get("char_count", 0),
                        page_count=file_data.get("page_count", 0),
                        extracted_text=file_data.get("extracted_text", "")[:10000],
                        summary=file_data.get("summary", ""),
                        markdown=file_data.get("markdown", ""),
                        content_blocks=file_data.get("content_blocks", []),
                        tables=file_data.get("tables", []),
                        images=file_data.get("images", []),
                        ocr_used=file_data.get("ocr_used", False),
                        agent_version=file_data.get("agent_version", ""),
                        processing_version=file_data.get("processing_version", ""),
                        parser_version=file_data.get("parser_version", ""),
                        ocr_engine=file_data.get("ocr_engine", ""),
                        tags=file_data.get("metadata", {}).get("tags", []),
                    )

                    # Persist extracted entities
                    entities = file_data.get("entities", [])
                    if entities:
                        from apps.documents.models import ExtractedEntity
                        ExtractedEntity.objects.bulk_create([
                            ExtractedEntity(
                                document=doc,
                                entity_type=e.get("type", "unknown"),
                                name=e.get("name", ""),
                                context=e.get("context", ""),
                                confidence=e.get("confidence"),
                                source="agent",
                            )
                            for e in entities
                            if e.get("name")
                        ])

                    document_ids.append(str(doc.id))
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
            "document_ids": document_ids,
            "pending_commands": AgentCommandSerializer(pending, many=True).data,
        })


# ---------------------------------------------------------------------------
# Helper functions for agent download
# ---------------------------------------------------------------------------


def _generate_config_yaml(agent_id: str, api_key: str, server_url: str, jwt_token: str = "") -> str:
    """Generate a config.yaml with pre-configured credentials and server URL.

    If jwt_token is provided, agent_id and api_key are left empty (binary auto-registers).
    If api_key is provided, agent_id is set (binary connects directly).
    """
    return f"""\
agent_name: edge-agent
agent_id: {agent_id}
data_dir: ~/.edge-agent
log_level: INFO
server:
  url: {server_url}
  api_key: {api_key}
  jwt_token: {jwt_token}
folders: []
scanner:
  ignore_patterns:
    - .git
    - .svn
    - .hg
    - __pycache__
    - node_modules
    - .DS_Store
    - Thumbs.db
    - "*.pyc"
    - "*.pyo"
    - "*.swp"
  max_file_size_mb: 100
ocr:
  engine: paddleocr
  lang: en
  use_gpu: false
  timeout_seconds: 120
parser:
  backend: pipeline
  effort: medium
  language: en
  formula_enable: true
  table_enable: true
sync:
  interval_minutes: 30
  batch_size: 50
  retry_attempts: 3
  retry_delay_seconds: 60
watcher:
  enabled: true
  recursive: true
  debounce_seconds: 2.0
llm:
  provider: openai
  model: gpt-4o-mini
  api_key: ""
  base_url: ""
  temperature: 0.3
  max_tokens: 4096
"""


def _generate_install_sh() -> str:
    """Generate a bash install script for Linux/macOS."""
    return """\
#!/bin/bash
set -e

INSTALL_DIR="$HOME/.edge-agent"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing Edge Agent..."
mkdir -p "$INSTALL_DIR"

# Copy binary (any platform name) and rename to "edge-agent"
cp "$SCRIPT_DIR"/edge-agent* "$INSTALL_DIR/edge-agent" 2>/dev/null || true
cp "$SCRIPT_DIR/config.yaml" "$INSTALL_DIR/"

# Make binary executable
chmod +x "$INSTALL_DIR/edge-agent"

echo ""
echo "Edge Agent installed to: $INSTALL_DIR"
echo ""
echo "Next steps:"
echo "  1. Add to PATH (optional):"
echo "     export PATH=\\"$INSTALL_DIR:\\$PATH\\""
echo ""
echo "  2. Start the agent:"
echo "     $INSTALL_DIR/edge-agent run"
echo ""
echo "  3. Or run in background:"
echo "     nohup $INSTALL_DIR/edge-agent run > /dev/null 2>&1 &"
echo ""
"""


def _generate_install_bat() -> str:
    """Generate a batch install script for Windows."""
    return """\
@echo off
setlocal

set INSTALL_DIR=%USERPROFILE%\\.edge-agent
set SCRIPT_DIR=%~dp0

echo Installing Edge Agent...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy binary (any platform name) and rename to edge-agent.exe
copy "%SCRIPT_DIR%edge-agent*.exe" "%INSTALL_DIR%\edge-agent.exe" >nul 2>&1
copy "%SCRIPT_DIR%config.yaml" "%INSTALL_DIR%\" >nul 2>&1

echo.
echo Edge Agent installed to: %INSTALL_DIR%
echo.
echo Next steps:
echo   1. Start the agent:
echo      %INSTALL_DIR%\\edge-agent.exe run
echo.
echo   2. Or add to PATH and run from anywhere:
echo      set PATH=%INSTALL_DIR%;%PATH%
echo      edge-agent run
echo.
pause
"""


def _generate_readme(agent_id: str, os_name: str) -> str:
    """Generate a README.txt for the downloaded zip."""
    return f"""\
Edge Agent - AI Archive Platform
=================================

Agent ID: {agent_id}
Platform: {os_name}

Quick Start
-----------

1. Extract this zip to a folder of your choice

2. Run the install script:
   - Linux/macOS: chmod +x install.sh && ./install.sh
   - Windows: Double-click install.bat

3. Start the agent:
   ~/.edge-agent/edge-agent run

Configuration
-------------

The config.yaml is pre-configured with your API key and server URL.
You can edit ~/.edge-agent/config.yaml to customize settings.

To add folders to monitor, edit config.yaml and add paths to the 'folders' list:
  folders:
    - /home/user/Documents
    - /home/user/Projects

Manual Installation
-------------------

1. Copy 'edge-agent' (or edge-agent.exe) to ~/.edge-agent/
2. Copy 'config.yaml' to ~/.edge-agent/
3. Run: ~/.edge-agent/edge-agent run

Troubleshooting
---------------

- Check logs: ~/.edge-agent/agent.log
- Test connection: ~/.edge-agent/edge-agent status
- View help: ~/.edge-agent/edge-agent --help
"""
