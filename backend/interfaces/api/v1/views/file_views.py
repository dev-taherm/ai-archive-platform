from __future__ import annotations

import uuid as _uuid

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from apps.files.models import FileRecord as FileRecordModel
from apps.organizations.mixins import OrgScopedMixin
from interfaces.api.v1.serializers.file_serializers import FileRecordSerializer

logger = logging.getLogger(__name__)


class FileRecordViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Viewset for browsing and deleting file records synced from edge agents."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"
    serializer_class = FileRecordSerializer

    def get_queryset(self):
        return self._org_qs(FileRecordModel.objects.all())

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        file_id = instance.id

        # Capture agent info before deletion (agent FK is SET_NULL on delete)
        agent = instance.agent

        from apps.documents.models import Document
        deleted_docs, _ = Document.objects.filter(file_id=file_id).delete()
        logger.info("Deleted %d document(s) for file %s", deleted_docs, file_id)

        instance.delete()
        logger.info("Deleted file record %s", file_id)

        # Push DELETE command to connected edge agent
        if agent is not None:
            try:
                from apps.agents.models import AgentCommand
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync

                channel_layer = get_channel_layer()
                command = AgentCommand.objects.create(
                    agent=agent,
                    command_type=AgentCommand.CommandType.DELETE,
                    payload={
                        "file_ids": [str(file_id)],
                        "local_path": instance.path or "",
                        "content_hash": instance.content_hash or "",
                    },
                )
                async_to_sync(channel_layer.group_send)(
                    f"agent_{agent.agent_id}",
                    {
                        "type": "push_command",
                        "command_id": str(command.id),
                        "command_type": command.command_type,
                        "payload": command.payload,
                    },
                )
            except Exception:
                logger.warning(
                    "Failed to push DELETE command to agent %s for file %s via WebSocket; "
                    "command saved in DB, agent will pick it up on next heartbeat.",
                    agent.agent_id,
                    file_id,
                )

        return Response(status=status.HTTP_204_NO_CONTENT)
