from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from interfaces.api.v1.serializers.search_serializers import (
    SearchQuerySerializer,
    SavedSearchSerializer,
    SearchHistorySerializer,
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
            date_from = request.query_params.get("date_from")
            if date_from:
                filters_data["date_from"] = date_from
            date_to = request.query_params.get("date_to")
            if date_to:
                filters_data["date_to"] = date_to
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

            # Log the search
            try:
                from apps.search.models import SearchLog

                SearchLog.objects.create(
                    user_id=request.user.pk if request.user.is_authenticated else None,
                    query=validated["query"],
                    search_type=validated.get("search_type", "hybrid"),
                    result_count=response_dto.total_count,
                    search_time_ms=response_dto.search_time_ms,
                    filters_used=filters_data,
                )
            except Exception:
                logger.debug("Failed to log search")

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

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """Return recent search history for the current user."""
        limit = min(int(request.query_params.get("limit", 20)), 100)
        from apps.search.models import SearchLog

        logs = SearchLog.objects.filter(
            user_id=request.user.pk
        ).order_by("-created_at")[:limit]

        return Response(
            SearchHistorySerializer(logs, many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get", "post", "delete"], url_path="saved")
    def saved(self, request):
        """Manage saved searches."""
        from apps.search.models import SavedSearch

        if request.method == "GET":
            searches = SavedSearch.objects.filter(
                user=request.user
            ).order_by("-created_at")
            return Response(
                SavedSearchSerializer(searches, many=True).data,
                status=status.HTTP_200_OK,
            )

        if request.method == "DELETE":
            search_id = request.data.get("id") or request.query_params.get("id")
            if not search_id:
                return Response(
                    {"detail": "id is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            deleted, _ = SavedSearch.objects.filter(
                id=search_id, user=request.user
            ).delete()
            if deleted:
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"detail": "Saved search not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # POST — create saved search
        serializer = SavedSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = serializer.save(user=request.user)
        return Response(
            SavedSearchSerializer(saved).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get", "post"], url_path="quick-search")
    def quick_search(self, request):
        """Lightweight search using the HybridSearchService directly.

        GET: /api/v1/search/quick-search/?q=query&top_k=5
        POST: {"query": "search text", "top_k": 5, "document_id": "optional-uuid"}
        """
        if request.method == "GET":
            query = request.query_params.get("q", "")
            top_k = int(request.query_params.get("top_k", 10))
            document_id = request.query_params.get("document_id")
        else:
            query = request.data.get("query", "")
            top_k = request.data.get("top_k", 10)
            document_id = request.data.get("document_id")

        if not query:
            return Response(
                {"detail": "Query is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from core.infrastructure.services.hybrid_search import HybridSearchService
            from core.infrastructure.services.vector_store import VectorStore

            vector_store = VectorStore()
            search_service = HybridSearchService(vector_store=vector_store)

            # Generate query embedding if provider available
            query_embedding = None
            try:
                from django.apps import apps
                ai_config = apps.get_app_config("ai")
                query_embedding = ai_config.embedding_provider.embed_text(query)
            except Exception:
                pass

            results = search_service.search(
                query=query,
                query_embedding=query_embedding,
                top_k=top_k,
                document_id=document_id,
                use_semantic=query_embedding is not None,
                use_keyword=True,
            )

            return Response(
                {
                    "query": query,
                    "results": [
                        {
                            "id": r.id,
                            "text": r.text,
                            "score": r.score,
                            "document_id": r.document_id,
                            "chunk_index": r.chunk_index,
                            "match_type": r.match_type,
                            "metadata": r.metadata,
                        }
                        for r in results
                    ],
                    "total_count": len(results),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Quick search failed: %s", e)
            return Response(
                {"detail": f"Search failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
