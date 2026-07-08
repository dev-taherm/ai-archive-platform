from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_invitation_email(
    self,
    invitation_id: str,
    organization_name: str,
    invited_email: str,
    role: str,
    invited_by_name: str,
    token: str,
) -> dict:
    """Send an invitation email to a user.

    Args:
        invitation_id: UUID of the Invitation record.
        organization_name: Name of the organization.
        invited_email: Email address of the invitee.
        role: Role they're being invited as (owner/admin/member).
        invited_by_name: Name of the person who sent the invite.
        token: Invitation token for the accept link.
    """
    try:
        # Build the invite URL — frontend will handle the accept flow
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        invite_url = f"{frontend_url}/invitations/accept?token={token}"

        subject = f"You've been invited to join {organization_name}"

        # Plain-text fallback
        plain_text = (
            f"{invited_by_name} has invited you to join {organization_name} "
            f"as a {role}.\n\n"
            f"Click the link below to accept the invitation:\n{invite_url}\n\n"
            f"This invitation expires in 7 days."
        )

        # HTML email
        try:
            html_message = render_to_string(
                "organizations/invitation_email.html",
                {
                    "organization_name": organization_name,
                    "invited_by_name": invited_by_name,
                    "role": role,
                    "invite_url": invite_url,
                },
            )
        except Exception:
            html_message = None

        send_mail(
            subject=subject,
            message=plain_text,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            recipient_list=[invited_email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info("Invitation email sent to %s for org %s", invited_email, organization_name)
        return {"status": "sent", "email": invited_email}

    except Exception as exc:
        logger.exception("Failed to send invitation email to %s", invited_email)
        raise self.retry(exc=exc)
