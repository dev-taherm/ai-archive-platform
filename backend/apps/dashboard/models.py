from django.db import models


class DashboardConfig(models.Model):
    """Stores per-user dashboard widget configuration."""

    class Meta:
        managed = False
        default_manager_name = "objects"
