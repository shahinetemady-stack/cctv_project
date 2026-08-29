"""
python manage.py import_doorbinkar_blog [--file scripts/output/doorbinkar_blog.json]

ایمپورت مقالات بلاگ سایت قدیمی doorbinkar.com.
slug همان slug لاتین قدیمی است و تاریخ انتشار شمسی به میلادی تبدیل
و روی created_at ست می‌شود (حفظ ترتیب و اعتبار تاریخ‌ها برای SEO).
"""

import json
import os
import re

import jdatetime
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.education.models import Article

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def parse_fa_datetime(text):
    """'1404/10/15 10:02:09' → datetime میلادی aware"""
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?", text.translate(FA_DIGITS))
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    try:
        dt = jdatetime.datetime(y, mo, d, h, mi, s).togregorian()
        return timezone.make_aware(dt)
    except ValueError:
        return None


class Command(BaseCommand):
    help = "ایمپورت مقالات بلاگ doorbinkar.com از JSON اسکریپر"

    def add_arguments(self, parser):
        parser.add_argument("--file", default="scripts/output/doorbinkar_blog.json")

    def handle(self, *args, **options):
        path = options["file"]
        if not os.path.exists(path):
            self.stderr.write(f"فایل یافت نشد: {path}")
            return

        data = json.load(open(path, encoding="utf-8"))
        created = updated = 0

        for row in data:
            defaults = {
                "title": row["title"][:300],
                "description": row.get("description") or "",
                "content": row.get("content") or "",
                "tags": row.get("tags") or [],
                "author": (row.get("author") or "")[:100],
                "is_published": True,
            }
            slug = (row.get("slug") or "").strip()[:320]
            article = Article.objects.filter(legacy_id=row["legacy_id"]).first()
            if article:
                for k, v in defaults.items():
                    setattr(article, k, v)
                article.save()
                updated += 1
            else:
                if slug and Article.objects.filter(slug=slug).exists():
                    slug = f"{slug}-{row['legacy_id']}"
                article = Article.objects.create(
                    legacy_id=row["legacy_id"], slug=slug, **defaults
                )
                created += 1

            # تصویر شاخص — فقط اگر ندارد
            if row.get("thumbnail") and not article.thumbnail:
                article.thumbnail = row["thumbnail"]
                article.save(update_fields=["thumbnail"])

            # تاریخ انتشار اصلی (auto_now_add را دور می‌زنیم)
            dt = parse_fa_datetime(row.get("date_fa") or "")
            if dt and article.created_at != dt:
                Article.objects.filter(pk=article.pk).update(created_at=dt)

        self.stdout.write(f"✓ ساخته شد: {created}")
        self.stdout.write(f"✓ به‌روزرسانی: {updated}")
