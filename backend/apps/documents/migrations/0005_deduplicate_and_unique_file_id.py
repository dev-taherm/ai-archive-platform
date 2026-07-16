from django.db import migrations, models


def deduplicate_documents(apps, schema_editor):
    from django.db.models import Count
    Document = apps.get_model("documents", "Document")
    duplicates = (
        Document.objects.values("file_id")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )
    for entry in duplicates:
        file_id = entry["file_id"]
        docs = Document.objects.filter(file_id=file_id).order_by("-created_at")
        keep = docs.first()
        to_delete = docs.exclude(id=keep.id)
        to_delete.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0004_document_organization_document_owner"),
    ]

    operations = [
        migrations.RunPython(deduplicate_documents, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="document",
            name="file_id",
            field=models.UUIDField(db_index=True, unique=True),
        ),
    ]
