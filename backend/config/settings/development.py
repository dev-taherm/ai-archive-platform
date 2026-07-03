from __future__ import annotations

from config.settings.base import *  # noqa: F401,F403

DEBUG: bool = True

ALLOWED_HOSTS: list[str] = ["*"]

# Local PostgreSQL overrides (optional – env vars take precedence)
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "localhost")  # noqa: F405
DATABASES["default"]["PORT"] = os.environ.get("POSTGRES_PORT", "5432")  # noqa: F405

CORS_ALLOW_ALL_ORIGINS: bool = True

# Relax throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "1000/hour",
    "user": "5000/hour",
}

EMAIL_BACKEND: str = "django.core.mail.backends.console.EmailBackend"
