from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from interfaces.api.v1.serializers.chat_serializers import (
    ChatMessageSerializer,
    ChatResponseSerializer,
    ChatSendMessageSerializer,
    ChatSessionCreateSerializer,
    ChatSessionSerializer,
)

logger = logging.getLogger(__name__)


class ChatViewSet(viewsets.GenericViewSet):
    """
    Chat ViewSet for conversational AI.

    Provides sessions (list, create) and messages (list, send) actions.
    Delegates all business logic to AIService.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create_session":
            return ChatSessionCreateSerializer
        if self.action == "send_message":
            return ChatSendMessageSerializer
        return ChatSessionSerializer

    @property
    def _chat_service(self):
        from django.apps import apps
        return apps.get_app_config("chat").chat_service

    @action(detail=False, methods=["get", "post"], url_path="sessions")
    def sessions(self, request):
        if request.method == "POST":
            return self._create_session(request)
        return self._list_sessions(request)

    def _list_sessions(self, request):
        return Response(
            {
                "sessions": [],
                "message": "Session listing requires a persistent session store.",
            },
            status=status.HTTP_200_OK,
        )

    def _create_session(self, request):
        serializer = ChatSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            session = self._chat_service.create_chat_session(
                user_id=request.user.pk,
                title=serializer.validated_data.get("title", ""),
            )
            return Response(
                ChatSessionSerializer(session).data,
                status=status.HTTP_201_CREATED,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=["get", "post"],
        url_path=r"sessions/(?P<session_id>[0-9a-f-]+)/messages",
    )
    def messages(self, request, session_id=None):
        if request.method == "POST":
            return self._send_message(request, session_id)
        return self._list_messages(request, session_id)

    def _list_messages(self, request, session_id):
        import uuid as _uuid
        try:
            session_uuid = _uuid.UUID(session_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid session ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            messages = self._chat_service.get_chat_history(
                session_uuid,
                limit=int(request.query_params.get("limit", 50)),
            )
            return Response(
                ChatMessageSerializer(messages, many=True).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    def _send_message(self, request, session_id):
        import uuid as _uuid
        try:
            session_uuid = _uuid.UUID(session_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid session ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChatSendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            response = self._chat_service.send_chat_message(
                session_id=session_uuid,
                message=serializer.validated_data["message"],
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                ChatResponseSerializer(response).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )
