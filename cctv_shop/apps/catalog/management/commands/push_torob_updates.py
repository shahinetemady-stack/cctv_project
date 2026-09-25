"""
کامند push_torob_updates — ارسال محصولات تغییرکرده به وب‌هوک ترب.
مجموعه «torob:dirty» را از کش می‌خواند و در بچ‌های ۱۰۰تایی به ترب اطلاع می‌دهد.
اجرا با cron سیستم (مثلاً هر ۵ دقیقه) تا حد ۲۰ درخواست/دقیقه ترب رعایت شود.
"""
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.catalog.torob import DIRTY_CACHE_KEY, send_webhook


class Command(BaseCommand):
    help = "ارسال محصولات تغییرکرده به وب‌هوک ترب (Torob Product Update Webhook)"

    def handle(self, *args, **options):
        if not getattr(settings, "TOROB_WEBHOOK_TOKEN", ""):
            self.stdout.write("TOROB_WEBHOOK_TOKEN تنظیم نشده — موردی ارسال نشد")
            return
        items = cache.get(DIRTY_CACHE_KEY) or []
        if not items:
            self.stdout.write("محصول تغییرکرده‌ای برای ارسال نیست")
            return
        cache.delete(DIRTY_CACHE_KEY)
        sent, message = send_webhook(items)
        if sent < len(items):
            # موارد ارسال‌نشده را برگردان تا دور بعد دوباره تلاش شوند
            remaining = cache.get(DIRTY_CACHE_KEY) or []
            cache.set(DIRTY_CACHE_KEY, remaining + items[sent:], timeout=None)
            self.stdout.write(self.style.WARNING(message))
            return
        self.stdout.write(self.style.SUCCESS(message))
