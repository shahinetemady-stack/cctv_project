"""
بازسازی بردارهای RAG (مشخصات + توضیحات + دیتاشیت محصولات) در rag_embeddings.json.
بعد از تغییر محصولات/دیتاشیت‌ها یا در کران هفتگی اجرا شود؛ اگر محتوا تغییر نکرده
باشد (اثر انگشت یکی) کاری نمی‌کند.

    python manage.py build_rag
"""

from django.core.management.base import BaseCommand

from apps.assistant import rag


class Command(BaseCommand):
    help = "بازسازی کش بردارهای RAG روی مشخصات/توضیحات/دیتاشیت محصولات"

    def handle(self, *args, **opts):
        result = rag.rebuild()
        if result["rebuilt"]:
            self.stdout.write(self.style.SUCCESS(
                f"بردارها بازسازی شدند — {result['chunks']} چانک"))
        else:
            self.stdout.write("محتوا تغییر نکرده — بازسازی لازم نبود "
                              f"({result['chunks']} چانک موجود)")
