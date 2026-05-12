"""
apps/orders/services.py
────────────────────────
Business logic layer for order management.
Controllers (views/API) call these functions — never write
order logic directly in views.

Functions:
  create_direct_order(user, cart)          → مشتری عمومی
  create_inquiry_order(user, inquiry_cart) → مشتری همکار
  confirm_inquiry_order(order, admin, confirmed_amount) → ادمین
  process_payment_callback(order, ref_id, success) → درگاه
  cancel_order(order, reason)
"""

import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, OrderItem, StockReservation


logger = logging.getLogger(__name__)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _create_stock_reservation(order: Order, variant, quantity: int) -> StockReservation:
    """رزرو موجودی برای یک variant و ثبت رکورد StockReservation."""
    reservation_minutes = getattr(settings, "RESERVATION_DURATION_MINUTES", 120)
    reserved_until = timezone.now() + timezone.timedelta(minutes=reservation_minutes)

    reservation = StockReservation.objects.create(
        variant=variant,
        order=order,
        quantity=quantity,
        reserved_until=reserved_until,
    )
    # stock را رزرو کن (فقط reserved_qty افزایش می‌یابد)
    variant.reserve(quantity)

    # لاگ حرکت موجودی
    StockMovement.objects.create(
        variant=variant,
        order=order,
        movement_type=StockMovement.MovementType.RESERVATION,
        quantity_change=quantity,
        stock_before=variant.stock_quantity,
        stock_after=variant.stock_quantity,  # stock_quantity عوض نمی‌شود
        note=f"رزرو برای سفارش {order.order_number}",
    )
    return reservation


def _check_and_alert_low_stock(variant) -> None:
    """اگر موجودی کم شد، هشدار ارسال کن."""
    threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if variant.available_stock <= threshold:
        from apps.notifications.services import notify_low_stock
        notify_low_stock(variant)


# ─── Direct Purchase (مشتری عمومی) ───────────────────────────────────────────

@transaction.atomic
def create_direct_order(user, cart) -> Order:
    """
    ساخت سفارش مستقیم از سبد خرید.
    موجودی را رزرو می‌کند اما هنوز کسر نمی‌کند.
    کاربر باید پرداخت کند تا موجودی واقعاً کسر شود.
    """
    items = list(cart.items.select_related("variant__product").all())
    if not items:
        raise ValueError("سبد خرید خالی است.")

    # بررسی موجودی همه آیتم‌ها قبل از ساخت سفارش
    for cart_item in items:
        if cart_item.variant.available_stock < cart_item.quantity:
            raise ValueError(
                f"موجودی کافی برای '{cart_item.variant.product.name}' وجود ندارد. "
                f"موجودی: {cart_item.variant.available_stock}"
            )

    # محاسبه مجموع
    total = sum(item.variant.final_price * item.quantity for item in items)

    # ساخت Order
    order = Order.objects.create(
        user=user,
        order_type=Order.OrderType.DIRECT_PURCHASE,
        status=Order.Status.AWAITING_PAYMENT,
        total_amount=total,
    )
    order.set_payment_deadline()

    # ساخت OrderItem‌ها و رزرو موجودی
    for cart_item in items:
        OrderItem.objects.create(
            order=order,
            variant=cart_item.variant,
            quantity=cart_item.quantity,
            unit_price=cart_item.variant.final_price,
        )
        _create_stock_reservation(order, cart_item.variant, cart_item.quantity)

    # خالی کردن سبد خرید
    cart.items.all().delete()

    logger.info(f"[ORDER] Direct order created: {order.order_number} | User: {user.phone}")
    return order


# ─── Inquiry Order (مشتری همکار) ─────────────────────────────────────────────

@transaction.atomic
def create_inquiry_order(user, inquiry_cart) -> Order:
    """
    ساخت سفارش استعلامی از سبد استعلام.
    موجودی در این مرحله رزرو نمی‌شود — بعد از تأیید ادمین رزرو می‌شود.
    """
    from apps.notifications.services import notify_inquiry_received

    items = list(inquiry_cart.items.select_related("variant__product").all())
    if not items:
        raise ValueError("سبد استعلام خالی است.")

    # قیمت snapshot (بدون نمایش به کاربر، فقط برای سوابق)
    total_snapshot = sum(item.variant.final_price * item.quantity for item in items)

    order = Order.objects.create(
        user=user,
        order_type=Order.OrderType.INQUIRY,
        status=Order.Status.PENDING,
        total_amount=total_snapshot,
        customer_notes=inquiry_cart.notes,
    )
    order.set_admin_confirm_deadline()

    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.variant.final_price,
        )

    # خالی کردن سبد استعلام
    inquiry_cart.items.all().delete()

    # ارسال پیامک به ادمین و کاربر (مرحله ۲)
    notify_inquiry_received(order)

    logger.info(f"[ORDER] Inquiry order created: {order.order_number} | User: {user.phone}")
    return order


# ─── Admin Confirmation (مرحله ۳) ─────────────────────────────────────────────

@transaction.atomic
def confirm_inquiry_order(order: Order, admin_user, confirmed_amount: int) -> Order:
    """
    ادمین سفارش استعلامی را تأیید می‌کند:
    1. قیمت نهایی را ثبت می‌کند
    2. موجودی را رزرو می‌کند (۲ ساعت)
    3. لینک پرداخت تولید می‌کند
    4. پیامک به مشتری ارسال می‌کند
    """
    from apps.notifications.services import notify_inquiry_confirmed

    if order.status != Order.Status.PENDING:
        raise ValueError(f"این سفارش در وضعیت '{order.get_status_display()}' است و قابل تأیید نیست.")

    # بررسی موجودی
    for item in order.items.select_related("variant").all():
        if item.variant.available_stock < item.quantity:
            raise ValueError(
                f"موجودی کافی برای '{item.variant.sku}' وجود ندارد. "
                f"موجودی: {item.variant.available_stock}"
            )

    # ثبت قیمت نهایی
    order.confirmed_amount = confirmed_amount
    order.status = Order.Status.AWAITING_PAYMENT
    order.admin_notes = (
        (order.admin_notes + "\n" if order.admin_notes else "")
        + f"تأیید توسط {admin_user} در {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    )
    order.save(update_fields=["confirmed_amount", "status", "admin_notes", "updated_at"])
    order.set_payment_deadline()

    # رزرو موجودی
    for item in order.items.select_related("variant").all():
        _create_stock_reservation(order, item.variant, item.quantity)
        item.confirmed_unit_price = confirmed_amount // order.items.count()  # تقسیم ساده
        item.reserved_until = order.payment_deadline
        item.save(update_fields=["confirmed_unit_price", "reserved_until", "updated_at"])

    # لینک پرداخت توسط /api/orders/bank/request/ تولید می‌شود
    # فعلاً فقط deadline را ذخیره می‌کنیم
    order.save(update_fields=["updated_at"])

    # پیامک به مشتری (مرحله ۴)
    notify_inquiry_confirmed(order)

    logger.info(f"[ORDER] Inquiry confirmed: {order.order_number} | Admin: {admin_user}")
    return order


# ─── Payment Callback ─────────────────────────────────────────────────────────

@transaction.atomic
def process_payment_callback(order: Order, ref_id: str, success: bool) -> Order:
    """
    پردازش callback درگاه پرداخت.
    اگر موفق: موجودی کسر شود، وضعیت PAID شود.
    اگر ناموفق: وضعیت تغییر نکند (کاربر می‌تواند دوباره تلاش کند).
    """
    from apps.notifications.services import notify_order_paid

    if order.status != Order.Status.AWAITING_PAYMENT:
        raise ValueError("این سفارش در وضعیت مناسب برای پرداخت نیست.")

    if not success:
        logger.warning(f"[PAYMENT] Failed payment for order {order.order_number}")
        return order

    # کسر موجودی واقعی
    for item in order.items.select_related("variant").all():
        stock_before = item.variant.stock_quantity
        item.variant.deduct_stock(item.quantity)
        StockMovement.objects.create(
            variant=item.variant,
            order=order,
            movement_type=StockMovement.MovementType.SALE,
            quantity_change=-item.quantity,
            stock_before=stock_before,
            stock_after=item.variant.stock_quantity,
            note=f"فروش پس از پرداخت سفارش {order.order_number}",
        )
        # آزاد کردن رکورد رزرو (نه موجودی — چون deduct_stock مراقب است)
        StockReservation.objects.filter(
            order=order, variant=item.variant, is_released=False
        ).update(
            is_released=True,
            released_at=timezone.now(),
            release_reason="payment_success",
        )
        _check_and_alert_low_stock(item.variant)

    order.status = Order.Status.PAID
    order.payment_ref_id = ref_id
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "payment_ref_id", "paid_at", "updated_at"])

    notify_order_paid(order)
    logger.info(f"[PAYMENT] Success: {order.order_number} | ref: {ref_id}")
    return order


# ─── Cancel Order ─────────────────────────────────────────────────────────────

@transaction.atomic
def cancel_order(order: Order, reason: str = "manual") -> Order:
    """
    کنسل کردن سفارش و آزاد کردن رزروها.
    """
    from apps.notifications.services import notify_order_cancelled

    cancellable_statuses = [Order.Status.PENDING, Order.Status.AWAITING_PAYMENT]
    if order.status not in cancellable_statuses:
        raise ValueError(f"سفارش در وضعیت '{order.get_status_display()}' قابل کنسل نیست.")

    # آزاد کردن رزروها
    for reservation in order.reservations.filter(is_released=False):
        reservation.release(reason=reason)

    order.status = Order.Status.CANCELLED
    order.admin_notes = (
        (order.admin_notes + "\n" if order.admin_notes else "")
        + f"[کنسل] دلیل: {reason} — {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    )
    order.save(update_fields=["status", "admin_notes", "updated_at"])

    notify_order_cancelled(order)
    logger.info(f"[ORDER] Cancelled: {order.order_number} | reason: {reason}")
    return order
