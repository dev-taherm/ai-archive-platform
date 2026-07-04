from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="documents.batch_process_documents")
def batch_process_documents(file_ids: list[str], user_id: str | None = None) -> dict[str, object]:
    """Batch process multiple documents using Celery chord.

    Returns summary of results. Individual document processing
    is dispatched as parallel subtasks.
    """
    from apps.documents.tasks import process_document_task

    task_ids: list[str] = []
    for fid in file_ids:
        result = process_document_task.delay(fid)
        task_ids.append(result.id)

    return {
        "batch_size": len(file_ids),
        "task_ids": task_ids,
        "status": "dispatched",
    }


@shared_task(name="documents.batch_classify_documents")
def batch_classify_documents(
    document_ids: list[str],
    categories: list[str] | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    """Classify multiple documents in parallel."""
    from apps.documents.tasks import classify_document_task

    task_ids: list[str] = []
    for doc_id in document_ids:
        result = classify_document_task.delay(doc_id, categories=categories)
        task_ids.append(result.id)

    return {
        "batch_size": len(document_ids),
        "task_ids": task_ids,
        "status": "dispatched",
    }


@shared_task(name="documents.batch_index_documents")
def batch_index_documents(document_ids: list[str], user_id: str | None = None) -> dict[str, object]:
    """Generate embeddings for multiple documents in parallel."""
    from apps.ai.tasks import generate_embeddings_task

    task_ids: list[str] = []
    for doc_id in document_ids:
        result = generate_embeddings_task.delay(doc_id, user_id=user_id)
        task_ids.append(result.id)

    return {
        "batch_size": len(document_ids),
        "task_ids": task_ids,
        "status": "dispatched",
    }


@shared_task(name="documents.reprocess_failed")
def reprocess_failed(user_id: str | None = None) -> dict[str, object]:
    """Reprocess all documents with 'failed' status."""
    from apps.documents.models import Document

    failed_docs = Document.objects.filter(processing_status="failed")
    doc_ids = [str(doc.id) for doc in failed_docs]

    if not doc_ids:
        return {"batch_size": 0, "status": "no_failed_documents"}

    return batch_process_documents(doc_ids, user_id=user_id)
