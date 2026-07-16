from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.documents.models import Document


class Command(BaseCommand):
    help = "Remove duplicate Document records, keeping the most recent per file_id"

    def handle(self, *args, **options):
        # Find file_ids with duplicates
        duplicates = (
            Document.objects.values("file_id")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
        )

        total_deleted = 0
        for entry in duplicates:
            file_id = entry["file_id"]
            docs = Document.objects.filter(file_id=file_id).order_by("-created_at")
            keep = docs.first()
            to_delete = docs.exclude(id=keep.id)
            count = to_delete.count()
            to_delete.delete()
            total_deleted += count
            self.stdout.write(f"  file_id={file_id}: kept {keep.id}, deleted {count} duplicates")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Found {len(duplicates)} duplicate groups, deleted {total_deleted} records."
        ))
