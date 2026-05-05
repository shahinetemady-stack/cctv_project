"""
apps/core/models.py
────────────────────
Abstract base models used across all apps.
Every concrete model inherits from TimeStampedModel to get
created_at and updated_at automatically.
"""

from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base class that adds created_at / updated_at
    to every model that inherits from it.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی",
    )

    class Meta:
        abstract = True


class SingletonModel(TimeStampedModel):
    """
    Abstract base for models that should only ever have ONE row.
    Used for ExchangeRateSetting.
    Calling .get_instance() always returns that single row,
    creating it with defaults if it doesn't exist yet.
    """

    class Meta:
        abstract = True

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        # Force pk=1 so there can never be a second row.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion of the singleton row.
        pass
