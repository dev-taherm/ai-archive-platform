"""Tool views — API endpoints for listing and executing chat tools."""

from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ToolViewSet(viewsets.GenericViewSet):
    """API endpoint for listing available tools and executing them directly."""

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="tools")
    def list_tools(self, request):
        """List all available tool definitions."""
        from core.application.tools import registry

        definitions = registry.get_definitions()
        tools = []
        for defn in definitions:
            func = defn.get("function", {})
            tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })
        return Response({"tools": tools}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="tools/execute")
    def execute_tool(self, request):
        """Execute a tool by name with given arguments."""
        from core.application.tools import registry

        tool_name = request.data.get("tool_name")
        arguments = request.data.get("arguments", {})

        if not tool_name:
            return Response(
                {"detail": "tool_name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = None
        except RuntimeError:
            loop = None

        try:
            import concurrent.futures

            if loop is None:
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        registry.execute(tool_name, arguments),
                    ).result(timeout=30)
            else:
                result = loop.run_until_complete(
                    registry.execute(tool_name, arguments)
                )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Tool execution failed")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
