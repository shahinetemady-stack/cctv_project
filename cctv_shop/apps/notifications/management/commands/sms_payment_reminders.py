"""
python manage.py sms_payment_reminders

یادآوری پیامکی سررسید بدهی به مشتریان — برای کران روزانه، مثلاً:
    0 9 * * * cd /path/to/cctv_shop && venv/bin/python manage.py sms_payment_reminders

برای هر قسط/سطر تسویه سررسیدگذشته روزی حداکثر یک پیامک ارسال می‌شود
(تکرار با NotificationLog کنترل می‌شود).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounting.models import SettlementLine
from apps.notifications.models import NotificationLog
from apps.notifications.services import notify_payment_reminder_sms


class Command(BaseCommand):
    help = "ارسال پیامک یادآوری سررسید بدهی (روزی یک بار برای هر سطر تسویه)"

    def handle(self, *args, **options):
        today = timezone.now().date()
        lines = (
            SettlementLine.objects
            .filter(is_active=True, due_date__lt=today, invoice__status="confirmed")
            .select_related("invoice", "invoice__customer")
        )
        sent = skipped = 0
        for line in lines:
            if line.remaining_amount <= 0:
                continue
            already = NotificationLog.objects.filter(
                channel="sms",
                subject=f"payment_reminder:{line.id}",
                status="sent",
                created_at__date=today,
            ).exists()
            if already:
                skipped += 1
                continue
            if notify_payment_reminder_sms(line):
                sent += 1
        self.stdout.write(self.style.SUCCESS(
            f"{sent} پیامک یادآوری ارسال شد ({skipped} مورد امروز قبلاً ارسال شده بود)"
        ))
