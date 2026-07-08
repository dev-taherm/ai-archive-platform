"""
Backfill existing data with a default organization and ownership.

Creates a "Default Organization", assigns all existing users to it,
and backfills the organization FK on all data models. For FileRecord
and Document, also infers ownership from agent/user relationships.
"""

from django.db import migrations


def create_default_org(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    org, _ = Organization.objects.get_or_create(
        slug="default",
        defaults={"name": "Default Organization", "description": "Auto-created for existing data."},
    )
    return org


def backfill_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Membership = apps.get_model("organizations", "Membership")
    org = create_default_org(apps, schema_editor)

    for user in User.objects.all():
        user.organization = org
        user.save(update_fields=["organization"])

        Membership.objects.get_or_create(
            user=user,
            organization=org,
            defaults={"role": "owner" if user.is_staff or user.is_superuser else "member"},
        )


def backfill_data_models(apps, schema_editor):
    org = apps.get_model("organizations", "Organization").objects.get(slug="default")

    models = [
        ("files", "FileRecord"),
        ("files", "AuditLog"),
        ("documents", "Document"),
        ("workflows", "Workflow"),
        ("workflows", "WorkflowRun"),
        ("reports", "Report"),
        ("chat", "ChatSession"),
        ("search", "SearchLog"),
        ("search", "SavedSearch"),
        ("agents", "Agent"),
        ("apikeys", "ApiKey"),
    ]

    for app_label, model_name in models:
        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        count = Model.objects.filter(organization__isnull=True).update(organization=org)
        if count:
            print(f"  Backfilled {count} {model_name} records")


def backfill_ownership(apps, schema_editor):
    """Infer owner for FileRecord and Document from agent/user relationships."""
    FileRecord = apps.get_model("files", "FileRecord")
    Agent = apps.get_model("agents", "Agent")
    Document = apps.get_model("documents", "Document")

    # FileRecord: set owner from agent's user
    agents = {str(a.id): a.user_id for a in Agent.objects.filter(user_id__isnull=False).only("id", "user_id")}

    updated = 0
    for fr in FileRecord.objects.filter(owner__isnull=True).select_related("agent"):
        if fr.agent_id and str(fr.agent_id) in agents:
            fr.owner_id = agents[str(fr.agent_id)]
            fr.save(update_fields=["owner"])
            updated += 1
    if updated:
        print(f"  Set owner on {updated} FileRecords via agent relationship")

    # Document: set owner from the file's owner
    file_owners = {str(fr.id): fr.owner_id for fr in FileRecord.objects.filter(owner_id__isnull=False).only("id", "owner_id")}

    updated = 0
    for doc in Document.objects.filter(owner__isnull=True):
        if str(doc.file_id) in file_owners:
            doc.owner_id = file_owners[str(doc.file_id)]
            doc.save(update_fields=["owner"])
            updated += 1
    if updated:
        print(f"  Set owner on {updated} Documents via file relationship")


def forward(apps, schema_editor):
    print("Creating default organization...")
    create_default_org(apps, schema_editor)

    print("Backfilling users...")
    backfill_users(apps, schema_editor)

    print("Backfilling data models...")
    backfill_data_models(apps, schema_editor)

    print("Backfilling ownership...")
    backfill_ownership(apps, schema_editor)

    print("Done.")


def backward(apps, schema_editor):
    Membership = apps.get_model("organizations", "Membership")
    Organization = apps.get_model("organizations", "Organization")

    Membership.objects.all().delete()
    Organization.objects.filter(slug="default").delete()

    models = [
        ("files", "FileRecord"), ("files", "AuditLog"), ("documents", "Document"),
        ("workflows", "Workflow"), ("workflows", "WorkflowRun"), ("reports", "Report"),
        ("chat", "ChatSession"), ("search", "SearchLog"), ("search", "SavedSearch"),
        ("agents", "Agent"), ("apikeys", "ApiKey"),
    ]

    for app_label, model_name in models:
        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        Model.objects.all().update(organization=None)

    User = apps.get_model("accounts", "User")
    User.objects.all().update(organization=None)


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("accounts", "0002_user_organization"),
        ("files", "0004_auditlog_organization_filerecord_organization_and_more"),
        ("documents", "0004_document_organization_document_owner"),
        ("workflows", "0002_workflow_organization_workflowrun_organization"),
        ("reports", "0002_report_organization"),
        ("chat", "0003_chatsession_organization"),
        ("search", "0003_savedsearch_organization_searchlog_organization"),
        ("agents", "0003_agent_organization"),
        ("apikeys", "0002_apikey_organization"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
