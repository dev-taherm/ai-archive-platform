from __future__ import annotations

import logging

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.apikeys.models import ApiKey

logger = logging.getLogger(__name__)


class ApiKeyAuthentication(BaseAuthentication):
    """
    Authenticates requests via X-API-Key header.

    If an X-API-Key header is present, the key is verified against the
    ApiKey model. Otherwise falls through to the next authentication class
    (typically JWT).
    """

    keyword = "X-API-Key"

    def authenticate(self, request):
        raw_key = request.META.get("HTTP_X_API_KEY")
        if not raw_key:
            return None

        api_key = ApiKey.verify_key(raw_key)
        if api_key is None:
            raise AuthenticationFailed("Invalid or inactive API key.")

        # Update last_used_at is handled by ApiKey.verify_key()
        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return self.keyword
