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


@shared_task(name="accounts.send_approval_notifications")
def send_approval_notifications() -> str:
    """Notify admins of pending user approvals."""
    from django.core.mail import send_mail
    from django.conf import settings

    pending = User.objects.filter(is_approved=False, is_active=True)
    admin_emails = list(
        User.objects.filter(is_staff=True, is_active=True, email__isnull=False)
        .values_list("email", flat=True)[:10]
    )

    if not pending.exists() or not admin_emails:
        return "No pending approvals or no admin emails"

    count = pending.count()
    send_mail(
        subject=f"{count} user(s) pending approval",
        message=f"There are {count} users awaiting approval on the AI Archive Platform.",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@archive.local"),
        recipient_list=admin_emails,
        fail_silently=True,
    )
    logger.info("Sent approval notification for %d pending users", count)
    return f"Notified admins about {count} pending users"


@shared_task(name="accounts.cleanup_expired_tokens")
def cleanup_expired_tokens() -> str:
    """Clean up expired JWT tokens from the blacklist."""
    from django.utils import timezone
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

    expired = OutstandingToken.objects.filter(expires_at__lt=timezone.now())
    count, _ = expired.delete()
    logger.info("Cleaned up %d expired tokens", count)
    return f"Cleaned up {count} expired tokens"
