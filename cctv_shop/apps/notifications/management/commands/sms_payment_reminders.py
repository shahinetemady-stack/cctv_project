"""
python manage.py sms_payment_reminders

یادآوری پیامکی سررسید بدهی به مشتریان — برای کران روزانه، مثلاً:
    0 9 * * * cd /path/to/cctv_shop && venv/bin/python manage.py sms_payment_reminders

برای هر قسط/سطر تسویه سررسیدگذشته روزی حداکثر یک پیامک ارسال می‌شود
(تکرار با NotificationLog کنترل می‌شود).
قاعدهٔ سررسید: نقدی ۳ روز پس از موعد (موعد نقدی = روز صدور)؛ توحسابی/یکماهه/
دوماهه از فردای موعد. هم فاکتورهای دستی و هم فاکتورهای سفارش سایت پوشش داده
می‌شوند (هر دو ردیف تسویه دارند).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.accounting.models import SettlementLine
from apps.notifications.models import NotificationLog
from apps.notifications.services import notify_payment_reminder_sms


class Command(BaseCommand):
    help = "ارسال پیامک یادآوری سررسید بدهی (روزی یک بار برای هر سطر تسویه)"

    def handle(self, *args, **options):
        today = timezone.localdate()
        cash_threshold = today - timedelta(days=3)
        lines = (
            SettlementLine.objects
            .filter(is_active=True, invoice__status="confirmed")
            .filter(
                Q(settlement_type="cash", due_date__lte=cash_threshold)
                | Q(settlement_type__in=["credit", "month1", "month2"], due_date__lt=today)
            )
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
