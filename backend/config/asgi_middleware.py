"""
WebSocket authentication middleware for Django Channels.

Supports three auth methods via query parameters:
- ?api_key=ak_... → API Key auth (for edge agents)
- ?token=eyJ...   → JWT token auth (for frontend/SPA)
- Cookie session   → Session auth (for browser clients)

Replaces AuthMiddlewareStack for more flexible multi-auth WS support.
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)

User = get_user_model()


@database_sync_to_async
def _verify_api_key(raw_key: str):
    """Verify an API key and return the user, or None."""
    from apps.apikeys.models import ApiKey

    api_key = ApiKey.verify_key(raw_key)
    if api_key is not None:
        return api_key.user
    return None


@database_sync_to_async
def _verify_jwt_token(token_str: str):
    """Verify a JWT token and return the user, or None."""
    try:
        token = AccessToken(token_str)
        return User.objects.get(pk=token["user_id"])
    except (TokenError, KeyError, User.DoesNotExist) as e:
        logger.debug("JWT token verification failed: %s", e)
        return None


@database_sync_to_async
def _get_user_from_session(session_key: str):
    """Look up user from Django session key."""
    from django.contrib.auth.models import AbstractBaseUser

    try:
        from django.contrib.sessions.models import Session

        session = Session.objects.get(session_key=session_key)
        data = session.get_decoded()
        user_id = data.get("_auth_user_id")
        if user_id:
            return User.objects.get(pk=user_id)
    except Exception:
        pass
    return None


class TokenAuthMiddleware(BaseMiddleware):
    """
    WebSocket auth middleware that checks query parameters for auth tokens.

    Priority: API Key > JWT > Session cookie > AnonymousUser

    Usage in asgi.py:
        from config.asgi_middleware import TokenAuthMiddleware
        application = ProtocolTypeRouter({
            "http": get_asgi_application(),
            "websocket": TokenAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            ),
        })
    """

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)

        # Parse query string
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)

        user = None

        # 1. Try API Key (for edge agents)
        api_key_values = params.get("api_key", [])
        if api_key_values:
            user = await _verify_api_key(api_key_values[0])
            if user is None:
                logger.warning("Invalid API key in WebSocket connection")
                await send({"type": "websocket.close", "code": 4401})
                return

        # 2. Try JWT token (for frontend/SPA)
        if user is None:
            token_values = params.get("token", [])
            if token_values:
                user = await _verify_jwt_token(token_values[0])
                if user is None:
                    logger.warning("Invalid JWT token in WebSocket connection")
                    await send({"type": "websocket.close", "code": 4401})
                    return

        # 3. Try session cookie auth (for browser clients)
        if user is None:
            cookies = scope.get("cookies", {})
            session_key = cookies.get("sessionid")
            if session_key:
                user = await _get_user_from_session(session_key)

        # Set user on scope
        scope["user"] = user or AnonymousUser()

        return await super().__call__(scope, receive, send)
