"""
apps/orders/management/commands/release_expired_reservations.py
────────────────────────────────────────────────────────────────
Management command to release expired stock reservations.

Run via cron every 15 minutes:
    */15 * * * * /path/to/venv/bin/python /path/to/manage.py release_expired_reservations

What this command does:
  1. پیدا کردن تمام StockReservation‌هایی که:
       - is_released = False  (هنوز آزاد نشده)
       - reserved_until < now  (زمانشان گذشته)
  2. فقط برای سفارش‌های «خرید مستقیم» (مشتری عمومی — پرداخت با درگاه):
       - اگر مشتری بستانکار باشد، سفارش از بستانکاری تسویه می‌شود (نه کنسل)
       - وگرنه رزرو آزاد و سفارش CANCELLED می‌شود
  3. سفارش‌های همکار/استعلامی دست‌نخورده می‌مانند — پرسنل وضعیتشان را تعیین می‌کند
  4. لاگ خروجی برای cron و بررسی اعداد
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, StockReservation


class Command(BaseCommand):
    help = "آزادسازی رزروهای منقضی‌شده و کنسل کردن سفارش‌های مرتبط"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="فقط نمایش دهد چه چیزی آزاد می‌شود، بدون تغییر واقعی در دیتابیس",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n{'[DRY RUN] ' if dry_run else ''}آزادسازی رزروهای منقضی — {timezone.localtime(now).strftime('%Y-%m-%d %H:%M:%S')}"
            )
        )

        # ── Step 1: پیدا کردن رزروهای منقضی ──────────────────────────────────
        expired_reservations = StockReservation.objects.filter(
            is_released=False,
            reserved_until__lt=now,
        ).select_related("variant__product", "order__user").order_by("order_id")

        count = expired_reservations.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("✓ هیچ رزرو منقضی‌ای یافت نشد."))
            return

        self.stdout.write(f"  → {count} رزرو منقضی یافت شد.")

        # ── Step 2 & 3: آزادسازی و کنسل کردن سفارش‌ها ──────────────────────

        released_count = 0
        cancelled_order_ids = set()

        # Group by order to decide which orders to cancel
        order_reservation_map: dict[int, list[StockReservation]] = {}
        for reservation in expired_reservations:
            order_id = reservation.order_id
            order_reservation_map.setdefault(order_id, []).append(reservation)

        for order_id, reservations in order_reservation_map.items():
            order = reservations[0].order  # already select_related

            # فقط سفارش‌های خرید مستقیم (مشتری عمومی — پرداخت با درگاه) خودکار
            # مدیریت می‌شوند؛ سفارش‌های همکار/استعلامی دست‌نخورده می‌مانند تا
            # پرسنل وضعیتشان را تعیین کند (رزروشان هم آزاد نمی‌شود)
            if order.order_type != Order.OrderType.DIRECT_PURCHASE:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ سفارش {order.order_number} همکار/استعلامی است — به پرسنل سپرده شد"
                    )
                )
                continue

            # فقط سفارش‌هایی که در وضعیت "در انتظار پرداخت" هستند کنسل می‌شوند
            if order.status != Order.Status.AWAITING_PAYMENT:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ سفارش {order.order_number} وضعیت '{order.get_status_display()}' دارد — رد شد"
                    )
                )
                continue

            self.stdout.write(
                f"  ● سفارش {order.order_number} ({order.user}) — {len(reservations)} رزرو"
            )

            if not dry_run:
                # قبل از کنسل: اگر مشتری بستانکار است سفارش از حسابش تسویه شود
                from apps.orders.services import try_settle_order_with_credit
                try:
                    if try_settle_order_with_credit(order):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"      ✓ سفارش {order.order_number} از بستانکاری مشتری تسویه شد (کنسل نشد)"
                            )
                        )
                        continue
                except Exception as exc:
                    # تسویه ناقص rollback شد — این نوبت کنسل نمی‌شود تا بررسی شود
                    self.stdout.write(
                        self.style.ERROR(
                            f"      ✗ خطا در تسویه از بستانکاری سفارش {order.order_number}: {exc}"
                        )
                    )
                    continue

                invoice = getattr(order, "sale_invoice", None)
                if invoice and (invoice.sale_payments.exists() or invoice.paid_amount > 0):
                    self.stdout.write(self.style.ERROR(
                        f"      ✗ سفارش {order.order_number} دریافت دارد؛ ابتدا سند دریافت باید برگشت بخورد"
                    ))
                    continue
                with transaction.atomic():
                    for reservation in reservations:
                        self.stdout.write(
                            f"      آزاد کردن {reservation.quantity}× "
                            f"{reservation.variant.sku} "
                            f"(reserved_qty: {reservation.variant.reserved_qty} → "
                            f"{max(0, reservation.variant.reserved_qty - reservation.quantity)})"
                        )
                        reservation.release(reason="expired")
                        released_count += 1

                    from apps.orders.services import cancel_order
                    order = cancel_order(order, reason="expired")
                    cancelled_order_ids.add(order_id)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"      ✓ سفارش {order.order_number} کنسل شد"
                        )
                    )
            else:
                # Dry-run: فقط نمایش
                for reservation in reservations:
                    self.stdout.write(
                        f"      [DRY] آزاد می‌شد: {reservation.quantity}× {reservation.variant.sku}"
                    )
                self.stdout.write(
                    f"      [DRY] سفارش {order.order_number} کنسل می‌شد"
                )

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] {count} رزرو و {len(order_reservation_map)} سفارش تحت تأثیر — بدون تغییر"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ تمام شد: {released_count} رزرو آزاد شد | "
                    f"{len(cancelled_order_ids)} سفارش کنسل شد"
                )
            )
