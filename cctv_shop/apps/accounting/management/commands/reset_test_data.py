"""
دستور reset_test_data — پاکسازی همه داده‌های تستی

استفاده:
  python manage.py reset_test_data
  python manage.py reset_test_data --confirm        # بدون پرسش، مستقیم اجرا
  python manage.py reset_test_data --purge-contacts # طرف حساب‌ها هم پاک شوند
  python manage.py reset_test_data --purge-accounts # حساب‌های بانکی هم پاک شوند
  python manage.py reset_test_data --confirm --purge-contacts --purge-accounts

این دستور:
  ✓ تمام فاکتورهای خرید (PurchaseInvoice, PurchaseItem, ExtraCost)
  ✓ تمام فاکتورهای فروش (SaleInvoice, SaleItem, SalePayment)
  ✓ تمام پرداخت‌ها (Payment)
  ✓ تمام سفارش‌های سایت (Order, OrderItem, StockReservation, PaymentLog)
  ✓ کاردکس انبار (StockMovement, StockTransfer)
  ✓ موجودی همه انبارها → صفر
  ✓ ProductVariant.stock_quantity و reserved_qty → صفر

محفوظ می‌ماند:
  - کاربران، Profile ها، StaffProfile ها، Role ها
  - محصولات، Variant ها، Category ها
  - انبارها
  - محتوای آموزشی (Article, Video, Page)
  - تنظیمات SEO و نرخ ارز
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "پاکسازی تمام داده‌های تستی (فاکتورها، سفارش‌ها، موجودی) — فقط برای ادمین اصلی"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="بدون پرسش اجرا کن",
        )
        parser.add_argument(
            "--purge-contacts",
            action="store_true",
            help="طرف حساب‌ها هم پاک شوند",
        )
        parser.add_argument(
            "--purge-accounts",
            action="store_true",
            help="حساب‌های بانکی هم پاک شوند",
        )

    def handle(self, *args, **options):
        confirm = options["confirm"]
        purge_contacts = options["purge_contacts"]
        purge_accounts = options["purge_accounts"]

        # نمایش هشدار
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("⚠️  هشدار: پاکسازی داده‌های تستی"))
        self.stdout.write(self.style.WARNING("━" * 60))
        self.stdout.write("این عملیات پاک می‌کند:")
        self.stdout.write("  • تمام فاکتورهای خرید و فروش")
        self.stdout.write("  • تمام پرداخت‌ها و سفارش‌های سایت")
        self.stdout.write("  • کاردکس انبار و موجودی همه کالاها")
        if purge_contacts:
            self.stdout.write(self.style.WARNING("  • طرف حساب‌ها"))
        if purge_accounts:
            self.stdout.write(self.style.WARNING("  • حساب‌های بانکی"))
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("محفوظ می‌ماند:"))
        self.stdout.write("  • کاربران، محصولات، انبارها، محتوا")
        self.stdout.write(self.style.WARNING("━" * 60))

        # تأیید
        if not confirm:
            self.stdout.write("")
            answer = input("برای ادامه تایپ کنید: YES\n> ")
            if answer.strip() != "YES":
                self.stdout.write(self.style.ERROR("لغو شد."))
                return

        # اجرای پاکسازی
        try:
            with transaction.atomic():
                from apps.accounting.models import (
                    PurchaseInvoice, PurchaseItem, ExtraCost,
                    SaleInvoice, SaleItem, SalePayment, Payment,
                    Contact, Account,
                )
                from apps.orders.models import (
                    Order, OrderItem, StockReservation, PaymentLog,
                )
                from apps.catalog.models import ProductVariant
                from apps.inventory.models import (
                    StockMovement, WarehouseStock, StockTransfer,
                )

                report = {
                    "purchase_invoices": PurchaseInvoice.objects.count(),
                    "sale_invoices": SaleInvoice.objects.count(),
                    "payments": Payment.objects.count(),
                    "orders": Order.objects.count(),
                    "stock_movements": StockMovement.objects.count(),
                    "variants": ProductVariant.objects.count(),
                }

                # فاکتورهای خرید
                ExtraCost.objects.all().delete()
                PurchaseItem.objects.all().delete()
                PurchaseInvoice.objects.all().delete()
                self.stdout.write(f"  ✓ {report['purchase_invoices']} فاکتور خرید پاک شد")

                # فاکتورهای فروش
                SalePayment.objects.all().delete()
                SaleItem.objects.all().delete()
                SaleInvoice.objects.all().delete()
                self.stdout.write(f"  ✓ {report['sale_invoices']} فاکتور فروش پاک شد")

                # پرداخت‌ها
                Payment.objects.all().delete()
                self.stdout.write(f"  ✓ {report['payments']} پرداخت پاک شد")

                # سفارش‌های سایت
                PaymentLog.objects.all().delete()
                StockReservation.objects.all().delete()
                OrderItem.objects.all().delete()
                Order.objects.all().delete()
                self.stdout.write(f"  ✓ {report['orders']} سفارش سایت پاک شد")

                # کاردکس
                StockTransfer.objects.all().delete()
                StockMovement.objects.all().delete()
                self.stdout.write(f"  ✓ {report['stock_movements']} حرکت کاردکس پاک شد")

                # WarehouseStock → صفر
                n_ws = WarehouseStock.objects.count()
                WarehouseStock.objects.all().update(quantity=0)
                self.stdout.write(f"  ✓ موجودی {n_ws} رکورد انبار صفر شد")

                # Variants → موجودی صفر
                ProductVariant.objects.all().update(
                    stock_quantity=0, reserved_qty=0,
                )
                self.stdout.write(f"  ✓ موجودی {report['variants']} variant صفر شد")

                # اختیاری
                if purge_contacts:
                    n = Contact.objects.count()
                    Contact.objects.all().delete()
                    self.stdout.write(f"  ✓ {n} طرف حساب پاک شد")

                if purge_accounts:
                    n = Account.objects.count()
                    Account.objects.all().delete()
                    self.stdout.write(f"  ✓ {n} حساب بانکی پاک شد")

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("✅ پاکسازی با موفقیت انجام شد."))
            self.stdout.write(self.style.SUCCESS("سیستم برای استفاده واقعی آماده است."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا: {e}"))
            import traceback
            traceback.print_exc()
