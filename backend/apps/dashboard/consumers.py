from __future__ import annotations

import json
import logging
from typing import Any

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time dashboard updates."""

    async def connect(self) -> None:
        self.user = self.scope.get("user")
        if self.user is None or self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f"dashboard_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        """Handle incoming messages from client."""
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        if msg_type == "subscribe_document":
            doc_id = data.get("document_id")
            if doc_id:
                await self.channel_layer.group_add(
                    f"document_{doc_id}", self.channel_name
                )
        elif msg_type == "unsubscribe_document":
            doc_id = data.get("document_id")
            if doc_id:
                await self.channel_layer.group_discard(
                    f"document_{doc_id}", self.channel_name
                )

    async def dashboard_update(self, event: dict[str, Any]) -> None:
        """Send dashboard update to WebSocket."""
        await self.send(text_data=json.dumps(event["data"]))

    async def document_update(self, event: dict[str, Any]) -> None:
        """Send document status update to WebSocket."""
        await self.send(text_data=json.dumps(event["data"]))


class ProcessingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time processing status updates."""

    async def connect(self) -> None:
        self.user = self.scope.get("user")
        if self.user is None or self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f"processing_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def processing_update(self, event: dict[str, Any]) -> None:
        """Send processing status update to WebSocket."""
        await self.send(text_data=json.dumps(event["data"]))

    async def task_completed(self, event: dict[str, Any]) -> None:
        """Send task completion notification to WebSocket."""
        await self.send(text_data=json.dumps(event["data"]))

    async def task_failed(self, event: dict[str, Any]) -> None:
        """Send task failure notification to WebSocket."""
        await self.send(text_data=json.dumps(event["data"]))
