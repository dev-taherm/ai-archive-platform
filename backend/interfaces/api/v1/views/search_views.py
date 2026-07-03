from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from interfaces.api.v1.serializers.search_serializers import (
    SearchFiltersSerializer,
    SearchQuerySerializer,
    SearchResponseSerializer,
)

logger = logging.getLogger(__name__)


class SearchView(viewsets.GenericViewSet):
    """
    Search endpoint supporting hybrid, semantic, and keyword modes.

    Delegates search execution to SearchService.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SearchQuerySerializer

    @property
    def _search_service(self):
        from django.apps import apps
        return apps.get_app_config("search").search_service

    @action(detail=False, methods=["get", "post"])
    def search(self, request):
        if request.method == "GET":
            data = {
                "query": request.query_params.get("q", ""),
                "search_type": request.query_params.get("type", "hybrid"),
                "max_results": int(request.query_params.get("max_results", 20)),
                "offset": int(request.query_params.get("offset", 0)),
            }
            filters_data = {}
            doc_types = request.query_params.get("doc_types")
            if doc_types:
                filters_data["doc_types"] = doc_types.split(",")
            languages = request.query_params.get("languages")
            if languages:
                filters_data["languages"] = languages.split(",")
            tags = request.query_params.get("tags")
            if tags:
                filters_data["tags"] = tags.split(",")
            min_score = request.query_params.get("min_score")
            if min_score:
                filters_data["min_score"] = float(min_score)
            if filters_data:
                data["filters"] = filters_data
        else:
            data = request.data

        serializer = SearchQuerySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        from core.application.dtos.search_dto import SearchFiltersDTO, SearchQueryDTO

        filters_dto = SearchFiltersDTO()
        filters_data = validated.get("filters", {})
        if filters_data:
            filters_dto = SearchFiltersDTO(
                doc_types=tuple(filters_data.get("doc_types", [])),
                languages=tuple(filters_data.get("languages", [])),
                tags=tuple(filters_data.get("tags", [])),
                date_from=filters_data.get("date_from"),
                date_to=filters_data.get("date_to"),
                min_score=filters_data.get("min_score", 0.0),
                file_extensions=tuple(filters_data.get("file_extensions", [])),
                exclude_duplicates=filters_data.get("exclude_duplicates", True),
            )

        query_dto = SearchQueryDTO(
            query=validated["query"],
            user_id=request.user.pk if request.user.is_authenticated else None,
            search_type=validated.get("search_type", "hybrid"),
            max_results=validated.get("max_results", 20),
            offset=validated.get("offset", 0),
            filters=filters_dto,
        )

        try:
            response_dto = self._search_service.search(
                query_dto,
                user_id=request.user.pk if request.user.is_authenticated else None,
            )

            results = []
            for r in response_dto.results:
                results.append({
                    "document_id": str(r.document_id),
                    "file_id": str(r.file_id),
                    "title": r.title,
                    "snippet": r.snippet,
                    "score": r.score,
                    "rank": r.rank,
                    "doc_type": r.doc_type,
                    "language": r.language,
                    "match_source": r.match_source,
                    "highlights": list(r.highlights),
                    "metadata": r.metadata,
                })

            return Response(
                {
                    "query": response_dto.query,
                    "results": results,
                    "total_count": response_dto.total_count,
                    "search_time_ms": response_dto.search_time_ms,
                    "search_type": response_dto.search_type,
                },
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )
