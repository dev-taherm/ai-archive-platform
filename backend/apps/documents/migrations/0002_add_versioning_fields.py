# Generated manually - adds versioning and pre-processing fields to Document

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="char_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="document",
            name="agent_version",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="document",
            name="processing_version",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="document",
            name="parser_version",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="document",
            name="ocr_engine",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="document",
            name="ocr_used",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="document",
            name="markdown",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="document",
            name="content_blocks",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="document",
            name="tables",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="document",
            name="images",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
