"""Backfill owner on FileRecord and Document from agent.user for existing synced data."""

from django.db import migrations


def backfill_owner_and_org(apps, schema_editor):
    """Set owner from agent.user on existing FileRecord/Document where owner is NULL."""
    FileRecord = apps.get_model("files", "FileRecord")
    Document = apps.get_model("documents", "Document")
    Agent = apps.get_model("agents", "Agent")

    # For each agent with an organization, assign org-scoped NULL-owner records
    for agent in Agent.objects.select_related("user").all():
        if agent.organization_id:
            FileRecord.objects.filter(
                organization=agent.organization,
                owner__isnull=True,
            ).update(owner=agent.user)

            Document.objects.filter(
                organization=agent.organization,
                owner__isnull=True,
            ).update(owner=agent.user)

    # For personal records (no org): if a user has exactly one agent,
    # assign all unowned personal records to them
    from django.contrib.auth import get_user_model
    User = apps.get_model("accounts", "User")
    for user in User.objects.all():
        user_agent_count = Agent.objects.filter(user=user).count()
        if user_agent_count == 1:
            agent = Agent.objects.filter(user=user).first()
            if agent and not agent.organization_id:
                FileRecord.objects.filter(
                    organization__isnull=True,
                    owner__isnull=True,
                ).update(owner=user)

                Document.objects.filter(
                    organization__isnull=True,
                    owner__isnull=True,
                ).update(owner=user)


def reverse_backfill(apps, schema_editor):
    """No-op reverse — we can't safely undo this."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("agents", "0004_add_sync_scope"),
        ("files", "0001_initial"),
        ("documents", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_owner_and_org, reverse_backfill),
    ]
