from __future__ import annotations

import uuid as _uuid

from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from apps.files.models import FileRecord as FileRecordModel
from apps.organizations.mixins import OrgScopedMixin
from interfaces.api.v1.serializers.file_serializers import FileRecordSerializer


class FileRecordViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for browsing file records synced from edge agents."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"
    serializer_class = FileRecordSerializer

    def get_queryset(self):
        return self._org_qs(FileRecordModel.objects.all())
