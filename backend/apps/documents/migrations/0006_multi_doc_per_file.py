"""Support multiple documents per file with page range fields."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_deduplicate_and_unique_file_id"),
    ]

    operations = [
        # Add the three new fields
        migrations.AddField(
            model_name="document",
            name="document_index",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Position within the file (0, 1, 2...)",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="page_start",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="First page number (1-based)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="page_end",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Last page number (1-based)",
                null=True,
            ),
        ),
        # Remove unique=True from file_id
        migrations.AlterField(
            model_name="document",
            name="file_id",
            field=models.UUIDField(db_index=True),
        ),
        # Add composite unique constraint
        migrations.AddConstraint(
            model_name="document",
            constraint=models.UniqueConstraint(
                fields=["file_id", "document_index"],
                name="unique_file_document_index",
            ),
        ),
    ]
