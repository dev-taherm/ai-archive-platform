from __future__ import annotations

import uuid

from django.db import models


class BaseModel(models.Model):
    """Abstract base model with UUID primary key and timestamp tracking.

    All domain-aligned models inherit from this to guarantee a consistent
    primary key type and automatic created_at / updated_at auditing.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
