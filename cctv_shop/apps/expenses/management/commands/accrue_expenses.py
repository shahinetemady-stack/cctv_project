"""صدور خودکار سند هزینه‌های ماه قبل — کرون روز اول ماه.

    35 8 1 * * root cd /opt/cctv/backend && /opt/cctv/venv/bin/python manage.py accrue_expenses >> /var/log/cctv-payroll.log 2>&1

قابل اجرای دستی: python manage.py accrue_expenses [سال میلادی] [ماه میلادی]
"""
from django.utils import timezone

from django.core.management.base import BaseCommand

from apps.expenses.services import accrue_month


class Command(BaseCommand):
    help = "صدور سند هزینه/بدهی ماه قبل (تکرارشونده + سود مشارکت)"

    def add_arguments(self, parser):
        parser.add_argument("year", nargs="?", type=int, help="سال میلادی (اختیاری)")
        parser.add_argument("month", nargs="?", type=int, help="ماه میلادی ۱-۱۲ (اختیاری)")

    def handle(self, *args, **options):
        year, month = options["year"], options["month"]
        if year and month:
            gy, gm = year, month
        else:
            today = timezone.localdate()
            gy, gm = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

        booked = accrue_month(gy, gm)
        self.stdout.write(self.style.SUCCESS(
            f"سند هزینه {gy}/{gm:02d} — تکرارشونده: {booked['recurring']}، "
            f"سود مشارکت: {booked['investor']}"
        ))
