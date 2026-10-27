"""
apps/education/signals.py
─────────────────────────
اطلاع‌رسانی IndexNow بعد از انتشار/ویرایش مقاله یا ویدیو.
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article, Video


@receiver(post_save, sender=Article)
def article_indexnow(sender, instance, **kwargs):
    if not instance.is_published:
        return
    from apps.core.indexnow import submit_urls
    submit_urls([f"{settings.SITE_URL.rstrip('/')}/blog/{instance.slug}/"])


@receiver(post_save, sender=Video)
def video_indexnow(sender, instance, **kwargs):
    if not instance.is_published:
        return
    from apps.core.indexnow import submit_urls
    submit_urls([f"{settings.SITE_URL.rstrip('/')}/videos/{instance.slug}/"])
