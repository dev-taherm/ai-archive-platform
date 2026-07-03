from __future__ import annotations

from config.settings.base import *  # noqa: F401,F403

DEBUG: bool = False

# Security
SECURE_BROWSER_XSS_FILTER: bool = True
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
SESSION_COOKIE_SECURE: bool = True
CSRF_COOKIE_SECURE: bool = True
SECURE_SSL_REDIRECT: bool = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"  # noqa: F405
SECURE_HSTS_SECONDS: int = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = True
SECURE_HSTS_PRELOAD: bool = True
X_FRAME_OPTIONS: str = "DENY"
SECURE_PROXY_SSL_HEADER: tuple[str, str] = ("HTTP_X_FORWARDED_PROTO", "https")

# Require HTTPS via env
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"  # noqa: F811

# Relax CSRF for API-only usage behind reverse proxy
CSRF_COOKIE_DOMAIN: str | None = os.environ.get("CSRF_COOKIE_DOMAIN", None)

# Static files served via Whitenoise or CDN – ensure collectstatic has run
STATICFILES_STORAGE: str = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Production CORS
CORS_ALLOWED_ORIGINS: list[str] = os.environ.get(  # noqa: F811
    "CORS_ALLOWED_ORIGINS", "https://localhost"
).split(",")

CORS_ALLOW_CREDENTIALS: bool = True  # noqa: F811

# Production email via SMTP
EMAIL_BACKEND: str = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST: str = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT: int = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER: str = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD: str = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS: bool = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
DEFAULT_FROM_EMAIL: str = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
