"""
python manage.py check_settlements
ارسال هشدار سررسید تسویه به مشتری و ادمین — برای کران روزانه، مثلاً:
    0 9 * * * cd /path/to/cctv_shop && venv/bin/python manage.py check_settlements
"""
from django.core.management.base import BaseCommand

from apps.orders.services import send_due_settlement_reminders, due_settlements_queryset


class Command(BaseCommand):
    help = "ارسال هشدار ایمیلی سررسید تسویه سفارش‌ها (روزی یک بار برای هر سفارش)"

    def handle(self, *args, **options):
        total = due_settlements_queryset().count()
        sent = send_due_settlement_reminders()
        self.stdout.write(self.style.SUCCESS(
            f"{total} سفارش سررسیدرسیده — {sent} هشدار ارسال شد"
        ))
