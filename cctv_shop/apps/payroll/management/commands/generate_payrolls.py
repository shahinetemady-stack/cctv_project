"""ایجاد/بازمحاسبه خودکار فیش حقوقی ماه قبل — اجرای زمان‌بندی‌شده سر ماه.

روش اجرا (کرون روز اول ماه ساعت ۸:۳۰ به وقت سرور):
    30 8 1 * * root cd /opt/cctv/backend && /opt/cctv/venv/bin/python manage.py generate_payrolls >> /var/log/cctv-payroll.log 2>&1

قابل اجرای دستی هم هست (سال/ماه میلادی — همان مقادیری که UI می‌فرستد):
    python manage.py generate_payrolls           # ماه قبل
    python manage.py generate_payrolls 2026 8    # ماه مشخص
"""
from datetime import date

from django.core.management.base import BaseCommand

from apps.payroll import services
from apps.payroll.models import Payslip


class Command(BaseCommand):
    help = "ساخت/بازمحاسبه فیش حقوقی ماه قبل (یا ماه میلادی داده‌شده) برای همه پرسنل فعال"

    def add_arguments(self, parser):
        parser.add_argument("year", nargs="?", type=int, help="سال میلادی (اختیاری)")
        parser.add_argument("month", nargs="?", type=int, help="ماه میلادی ۱-۱۲ (اختیاری)")

    def handle(self, *args, **options):
        year, month = options["year"], options["month"]
        if year and month:
            gy, gm = year, month
        else:
            today = date.today()
            gy, gm = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

        result = services.generate_month(gy, gm)
        total = Payslip.objects.filter(year=gy, month=gm).count()
        booked = services.accrue_month(gy, gm)
        self.stdout.write(self.style.SUCCESS(
            f"فیش {gy}/{gm:02d} — ساخته‌شده: {result['created']}، "
            f"به‌روزشده: {result['updated']}، ردشده (پرداخت‌شده): {result['skipped']}، "
            f"مجموع فیش‌های ماه: {total}، سند هزینه/بدهی صادرشده: {booked}"
        ))
