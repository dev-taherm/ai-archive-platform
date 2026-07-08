from __future__ import annotations

import logging

from celery import shared_task
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(name="accounts.deactivate_inactive_users")
def deactivate_inactive_users(days_inactive: int = 90) -> str:
    """Deactivate users who have not logged in for the specified number of days."""
    from datetime import timedelta

    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=days_inactive)
    users = User.objects.filter(
        last_login__lt=cutoff,
        is_active=True,
        is_superuser=False,
    )
    count = users.update(is_active=False)
    logger.info("Deactivated %d users inactive for %d days", count, days_inactive)
    return f"Deactivated {count} users"


@shared_task(name="accounts.cleanup_expired_tokens")
def cleanup_expired_tokens() -> str:
    """Clean up expired JWT tokens from the blacklist."""
    from django.utils import timezone
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

    expired = OutstandingToken.objects.filter(expires_at__lt=timezone.now())
    count, _ = expired.delete()
    logger.info("Cleaned up %d expired tokens", count)
    return f"Cleaned up {count} expired tokens"
