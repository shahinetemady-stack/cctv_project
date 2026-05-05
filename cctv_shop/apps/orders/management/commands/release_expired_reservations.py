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
  2. آزاد کردن هر رزرو:
       - variant.reserved_qty -= reservation.quantity  (فقط reserved_qty)
       - stock_quantity دست نمی‌خورد
  3. تغییر وضعیت سفارش‌های مرتبط به CANCELLED
       (فقط اگر همه آیتم‌های سفارش آزاد شده باشند)
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
                f"\n{'[DRY RUN] ' if dry_run else ''}آزادسازی رزروهای منقضی — {now.strftime('%Y-%m-%d %H:%M:%S')}"
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
                with transaction.atomic():
                    # آزاد کردن هر رزرو
                    for reservation in reservations:
                        self.stdout.write(
                            f"      آزاد کردن {reservation.quantity}× "
                            f"{reservation.variant.sku} "
                            f"(reserved_qty: {reservation.variant.reserved_qty} → "
                            f"{max(0, reservation.variant.reserved_qty - reservation.quantity)})"
                        )
                        reservation.release(reason="expired")
                        released_count += 1

                    # کنسل کردن سفارش
                    order.status = Order.Status.CANCELLED
                    order.admin_notes = (
                        (order.admin_notes + "\n" if order.admin_notes else "")
                        + f"[AUTO] کنسل شد — مهلت پرداخت منقضی — {now.strftime('%Y-%m-%d %H:%M')}"
                    )
                    order.save(update_fields=["status", "admin_notes", "updated_at"])
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
