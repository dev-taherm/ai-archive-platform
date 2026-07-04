from __future__ import annotations

from django.http import JsonResponse
from django.views import View


class HealthCheckView(View):
    """Simple health check endpoint for Docker and load balancers."""

    def get(self, request):
        return JsonResponse({"status": "healthy"})
