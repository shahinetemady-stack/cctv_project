"""اصلاح یک‌بارهٔ تاریخ اسنادی که با مبنای UTC (به‌جای تهران) ثبت شده‌اند.

قانون: اگر date رکورد برابر «تاریخ UTCِ لحظهٔ created_at» باشد ولی با «تاریخ تهرانِ
همان لحظه» فرق کند، یعنی تاریخ از پیش‌فرض UTC آمده (نه انتخاب دستی ادمین) و باید
به تاریخ تهران اصلاح شود. رکوردهایی که date‌شان با هر دو فرق دارد (انتخاب دستی)
دست نمی‌خورند.

اجرا: python manage.py fix_document_dates_tz          → dry-run (فقط گزارش)
      python manage.py fix_document_dates_tz --apply  → اعمال
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounting.models import (
    PurchaseInvoice, Payment, SalePayment, ReturnInvoice,
)
from apps.expenses.models import ExpenseCharge, InvestorMovement
from apps.payroll.models import LeaveRecord, BonusPenaltyRecord

TARGETS = [
    (PurchaseInvoice, "date"),
    (Payment, "date"),
    (SalePayment, "date"),
    (ReturnInvoice, "date"),
    (ExpenseCharge, "date"),
    (InvestorMovement, "date"),
    (LeaveRecord, "date"),
    (BonusPenaltyRecord, "date"),
]


class Command(BaseCommand):
    help = "اصلاح تاریخ اسناد از مبنای UTC به تهران (فقط رکوردهای پیش‌فرض‌خورده)"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="اعمال واقعی (بدون آن فقط گزارش)")

    def handle(self, *args, **options):
        apply = options["apply"]
        total = 0
        for model, field in TARGETS:
            for obj in model.objects.all().only("id", field, "created_at"):
                d = getattr(obj, field)
                if not d:
                    continue
                utc_d = timezone.localtime(obj.created_at, datetime.timezone.utc).date()
                teh_d = timezone.localdate(obj.created_at)
                if d == utc_d and utc_d != teh_d:
                    total += 1
                    self.stdout.write(
                        f"{'FIX' if apply else 'DRY'} {model.__name__}#{obj.id}: {d} → {teh_d}"
                    )
                    if apply:
                        setattr(obj, field, teh_d)
                        obj.save(update_fields=[field])
        self.stdout.write(self.style.SUCCESS(
            f"{'اصلاح شد' if apply else 'نیازمند اصلاح (dry-run)'}: {total} سند"
        ))
