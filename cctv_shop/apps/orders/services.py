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
from datetime import timedelta
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
    return reservation


def _check_and_alert_low_stock(variant) -> None:
    """اگر موجودی کم شد، هشدار ارسال کن."""
    threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if variant.available_stock <= threshold:
        from apps.notifications.services import notify_low_stock
        notify_low_stock(variant)

def _add_package_order_items(order, cart_item) -> None:
    """آیتم پکیج سبد به اقلام اجزایش باز می‌شود.
    تخفیف پکیج به نسبت قیمت هر قلم سرشکن می‌شود و باقیماندهٔ گردکردن روی یک قلم
    یک‌عددی (یا بزرگ‌ترین قلم) اعمال می‌شود تا جمع اقلام دقیقاً برابر
    قیمت پکیج × تعداد بسته باشد — از نظر حسابداری هر قطعه جداگانه در فاکتور و
    کاردکس ثبت می‌شود."""
    from apps.orders.models import settlement_due_for
    from apps.catalog.pricing import price_for_user

    pkg = cart_item.package
    bundles = cart_item.quantity
    user = order.user
    comps = list(pkg.package_items.select_related("variant").all())
    if not comps:
        return
    # مبنای قیمت اقلام همان قیمت نمایشی کاربر است تا فاکتور با صفحه پکیج یکی باشد
    original, final = pkg.prices_for(user)
    factor = (final / original) if original else 1
    unit_prices = [round(price_for_user(c.variant, user) * factor) for c in comps]
    diff = final - sum(p * c.quantity for p, c in zip(unit_prices, comps))
    if diff:
        ones = [i for i, c in enumerate(comps) if c.quantity == 1]
        target_idx = ones[0] if ones else max(
            range(len(comps)), key=lambda i: unit_prices[i] * comps[i].quantity
        )
        unit_prices[target_idx] += diff // comps[target_idx].quantity
    for c, price in zip(comps, unit_prices):
        OrderItem.objects.create(
            order=order,
            variant=c.variant,
            quantity=c.quantity * bundles,
            unit_price=price,
            settlement_type=cart_item.settlement_type,
            settlement_due_date=settlement_due_for(cart_item.settlement_type),
        )


# ─── Direct Purchase (مشتری عمومی و سیلور) ───────────────────────────────────

def _create_sale_invoice_for_order(order: Order, created_by=None):
    """
    ساخت فاکتور فروش برای سفارش — فقط بعد از تأیید پرداخت صدا زده می‌شود
    (callback موفق درگاه در process_payment_callback یا تأیید فیش توسط ادمین)،
    نه هنگام چک‌اوت؛ تا فاکتور پرداخت‌نشده در حسابداری نماند.
    """
    from apps.accounting.models import SaleInvoice, SaleItem, SettlementLine
    from apps.orders.models import settlement_due_for

    items = list(order.items.select_related("variant").all())
    today = timezone.now().date()
    invoice = SaleInvoice.objects.create(
        source=SaleInvoice.InvoiceSource.ORDER,
        status=SaleInvoice.Status.CONFIRMED,
        order=order,
        customer=order.user,
        customer_name=order.user.get_full_name(),
        customer_phone=order.user.phone,
        settlement=SaleInvoice.Settlement.CASH,
        due_date=None,
        created_by=created_by,
    )
    for item in items:
        SaleItem.objects.create(
            invoice=invoice,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.confirmed_unit_price or item.unit_price,
        )
    # برای هر نوع تسویه یک ردیف (سفارش مستقیم تمام‌نقدی است ولی این عمومی نگه داشته شده)
    totals_by_type = {}
    for item in items:
        price = item.confirmed_unit_price or item.unit_price
        totals_by_type[item.settlement_type] = (
            totals_by_type.get(item.settlement_type, 0) + price * item.quantity
        )
    for st, amount in totals_by_type.items():
        SettlementLine.objects.create(
            invoice=invoice,
            settlement_type=st,
            amount=amount,
            due_date=settlement_due_for(st, today),
        )
    return invoice


def _auto_confirm_cash_order(order: Order) -> bool:
    """
    تأیید خودکار سفارش مستقیم تمام‌نقدی (تا سقف DIRECT_PURCHASE_MAX_RIAL) —
    بدون نیاز به تأیید ادمین: رزرو موجودی + AWAITING_PAYMENT
    تا مشتری بلافاصله با درگاه پرداخت کند.
    فاکتور فروش اینجا ساخته نمی‌شود — بعد از پرداخت موفق ساخته می‌شود.
    اگر موجودی کافی نباشد False برمی‌گرداند و سفارش PENDING می‌ماند (مسیر تأیید ادمین).
    """
    items = list(order.items.select_related("variant").all())
    for item in items:
        if item.variant.available_stock < item.quantity:
            logger.warning(f"[ORDER] Auto-confirm skipped (stock): {order.order_number}")
            return False

    order.confirmed_amount = order.total_amount
    order.status = Order.Status.AWAITING_PAYMENT
    order.save(update_fields=["confirmed_amount", "status", "updated_at"])
    order.set_payment_deadline()

    for item in items:
        _create_stock_reservation(order, item.variant, item.quantity)
        item.confirmed_unit_price = item.unit_price
        item.reserved_until = order.payment_deadline
        item.save(update_fields=["confirmed_unit_price", "reserved_until", "updated_at"])

    logger.info(f"[ORDER] Auto-confirmed cash order: {order.order_number} | {order.total_amount} rials")
    return True


@transaction.atomic
def create_direct_order(user, cart) -> list:
    """
    ساخت سفارش مستقیم از سبد خرید.
    سفارش تمام‌نقدی تا سقف DIRECT_PURCHASE_MAX_RIAL خودکار تأیید می‌شود
    (AWAITING_PAYMENT) و مشتری بلافاصله به درگاه می‌رود؛ بالای سقف رد می‌شود.
    سفارش دارای قلم اعتباری مثل قبل PENDING می‌ماند (تأیید ادمین).
    برای هر نوع تسویه یک سفارش جدا ساخته می‌شود.
    خروجی: لیست سفارش‌ها (۱ تا ۴).
    """
    from apps.orders.models import settlement_due_for

    items = list(cart.items.select_related("variant__product").all())
    if not items:
        raise ValueError("سبد خرید خالی است.")

    grand_total = sum(item.subtotal for item in items)
    all_cash = all(i.settlement_type == Order.Settlement.CASH for i in items)
    max_amount = getattr(settings, "DIRECT_PURCHASE_MAX_RIAL", 300_000_000)
    if all_cash and grand_total > max_amount:
        raise ValueError(
            f"سقف خرید مستقیم با پرداخت آنلاین {max_amount:,} ریال است. "
            "برای خرید بیشتر با فروشگاه تماس بگیرید."
        )

    # سقف تعداد هنگام افزودن به سبد اعمال شده (CartView) — اقلام سبد بیشتر از موجودی قابل فروش نیستند
    groups = {st: [i for i in items if i.settlement_type == st] for st in Order.Settlement.values}

    orders = []
    for st, group in groups.items():
        if not group:
            continue
        total = sum(item.subtotal for item in group)
        order = Order.objects.create(
            user=user,
            order_type=Order.OrderType.DIRECT_PURCHASE,
            status=Order.Status.PENDING,
            total_amount=total,
            settlement_type=st,
            settlement_due_date=settlement_due_for(st),
        )
        order.set_admin_confirm_deadline()
        for cart_item in group:
            if cart_item.package_id:
                _add_package_order_items(order, cart_item)
            else:
                OrderItem.objects.create(
                    order=order,
                    variant=cart_item.variant,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                    settlement_type=cart_item.settlement_type,
                    settlement_due_date=settlement_due_for(cart_item.settlement_type),
                )
        # جمع واقعی اقلام مرجع است (پکیج‌ها بعد از سرشکنِ تخفیف و گردکردن باز شده‌اند)
        order.total_amount = sum(i.subtotal for i in order.items.all())
        order.save(update_fields=["total_amount", "updated_at"])
        orders.append(order)

    # خالی کردن سبد خرید
    cart.items.all().delete()

    # مسیر سریع: سفارش تمام‌نقدی تا سقف → تأیید خودکار و پرداخت فوری با درگاه
    if all_cash:
        for order in orders:
            _auto_confirm_cash_order(order)

    logger.info(f"[ORDER] Direct orders created: {[o.order_number for o in orders]} | User: {user.phone}")
    return orders

# ─── Inquiry Order (مشتری همکار) ─────────────────────────────────────────────

@transaction.atomic
def create_inquiry_order(user, inquiry_cart) -> list:
    """
    ساخت سفارش استعلامی از سبد استعلام — خروجی لیست سفارش‌ها (۱ تا ۴).
    برای هر نوع تسویه (نقدی/تو حسابی/یکماهه/دوماهه) یک سفارش جدا ساخته می‌شود
    تا موعد تسویه و تخصیص خودکار واریزی‌ها بین انواع تسویه قاطی نشود.
    موجودی در این مرحله رزرو نمی‌شود — بعد از تأیید ادمین رزرو می‌شود.
    """
    from apps.notifications.services import notify_inquiry_received

    items = list(inquiry_cart.items.select_related("variant__product").all())
    if not items:
        raise ValueError("سبد استعلام خالی است.")

    from apps.catalog.pricing import price_for_settlement
    from apps.orders.models import settlement_due_for

    groups = {st: [i for i in items if i.settlement_type == st] for st in Order.Settlement.values}

    orders = []
    for st, group in groups.items():
        if not group:
            continue
        due_date = settlement_due_for(st) if st != Order.Settlement.CASH else None
        total_snapshot = sum(
            price_for_settlement(item.variant, user, item.settlement_type) * item.quantity
            for item in group
        )
        order = Order.objects.create(
            user=user,
            order_type=Order.OrderType.INQUIRY,
            status=Order.Status.PENDING,
            total_amount=total_snapshot,
            customer_notes=inquiry_cart.notes,
            settlement_type=st,
            settlement_due_date=due_date,
        )
        order.set_admin_confirm_deadline()
        for item in group:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                unit_price=price_for_settlement(item.variant, user, item.settlement_type),
                settlement_type=item.settlement_type,
                settlement_due_date=settlement_due_for(item.settlement_type),
            )
        orders.append(order)

    # خالی کردن سبد استعلام
    inquiry_cart.items.all().delete()

    # ارسال پیامک به ادمین و کاربر (مرحله ۲) — برای هر سفارش
    for order in orders:
        notify_inquiry_received(order)

    logger.info(f"[ORDER] Inquiry orders created: {[o.order_number for o in orders]} | User: {user.phone}")
    return orders


# ─── Admin Confirmation (مرحله ۳) ─────────────────────────────────────────────

@transaction.atomic
def confirm_inquiry_order(order: Order, admin_user, confirmed_amount: int,
                          settlement_type: str = None, settlement_due_date=None,
                          sarraf_account_number: str = "", sarraf_account_holder: str = "",
                          staff=None) -> Order:
    """
    ادمین سفارش استعلامی را تأیید می‌کند:
    1. قیمت نهایی را ثبت می‌کند
    2. موجودی را رزرو می‌کند (۲ ساعت)
    3. لینک پرداخت تولید می‌کند
    4. پیامک به مشتری ارسال می‌کند
    5. فاکتور فروش + ردیف‌های تسویه (per settlement_type) می‌سازد
    نحوه تسویه و موعد آن هم در همین مرحله قابل تعیین/بازنویسی است.
    اگر سفارش قلم نقدی داشته باشد → AWAITING_PAYMENT (با مهلت پرداخت)،
    وگرنه (همه اعتباری) → READY_TO_SHIP (مستقیم به مرحله ارسال می‌رود).
    """
    from apps.notifications.services import notify_inquiry_confirmed
    from apps.orders.models import settlement_due_for

    if order.status != Order.Status.PENDING:
        raise ValueError(f"این سفارش در وضعیت '{order.get_status_display()}' است و قابل تأیید نیست.")

    # کنترل سقف اعتبار — سهم غیرنقدی سفارش (به نسبت ارزش اقلام از مبلغ تأییدشده)
    _items = list(order.items.select_related("variant").all())
    _base = sum(i.unit_price * i.quantity for i in _items) or confirmed_amount
    _non_cash = sum(
        round(confirmed_amount * (i.unit_price * i.quantity) / _base)
        for i in _items if i.settlement_type != Order.Settlement.CASH
    )
    if _non_cash > 0:
        from apps.accounting.services import check_credit_limit
        _err = check_credit_limit(order.user, _non_cash)  # مبالغ سفارش ریال است
        if _err:
            raise ValueError(_err)

    # بررسی موجودی
    for item in order.items.select_related("variant").all():
        if item.variant.available_stock < item.quantity:
            raise ValueError(
                f"موجودی کافی برای '{item.variant.sku}' وجود ندارد. "
                f"موجودی: {item.variant.available_stock}"
            )

    # ثبت قیمت نهایی — سفارش نقدی به درگاه/فیش می‌رود، سفارش کاملاً اعتباری مستقیم به ارسال
    has_cash_item = order.items.filter(settlement_type=Order.Settlement.CASH).exists()
    order.confirmed_amount = confirmed_amount
    order.updated_by = staff or admin_user
    order.status = Order.Status.AWAITING_PAYMENT if has_cash_item else Order.Status.READY_TO_SHIP
    update_fields = ["confirmed_amount", "status", "admin_notes", "updated_by", "updated_at"]
    if settlement_type in Order.Settlement.values:
        order.settlement_type = settlement_type
        update_fields.append("settlement_type")
    if settlement_due_date:
        order.settlement_due_date = settlement_due_date
        update_fields.append("settlement_due_date")
    order.admin_notes = (
        (order.admin_notes + "\n" if order.admin_notes else "")
        + f"تأیید توسط {admin_user} در {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    )
    order.save(update_fields=update_fields)
    if has_cash_item:
        order.set_payment_deadline()

    # رزرو موجودی + توزیع مبلغ تأییدشده روی اقلام به نسبت ارزش هر قلم
    # (تقسیم مساوی قدیمی برای اقلام با قیمت متفاوت قیمت هر قلم را خراب می‌کرد)
    items = list(order.items.select_related("variant").all())
    base_total = sum(i.unit_price * i.quantity for i in items) or confirmed_amount
    remaining = confirmed_amount
    for idx, item in enumerate(items):
        _create_stock_reservation(order, item.variant, item.quantity)
        if idx == len(items) - 1:
            item.confirmed_unit_price = remaining // item.quantity if item.quantity else 0
        else:
            share = round(confirmed_amount * (item.unit_price * item.quantity) / base_total)
            item.confirmed_unit_price = share // item.quantity if item.quantity else 0
            remaining -= item.confirmed_unit_price * item.quantity
        item.reserved_until = order.payment_deadline
        item.save(update_fields=["confirmed_unit_price", "reserved_until", "updated_at"])

    # لینک پرداخت توسط /api/orders/bank/request/ تولید می‌شود
    # فعلاً فقط deadline را ذخیره می‌کنیم
    order.save(update_fields=["updated_at"])

    # ── اطلاعات صراف ───────────────────────────────────────────────────
    order.sarraf_account_number = sarraf_account_number or ""
    order.sarraf_account_holder = sarraf_account_holder or ""
    order.save(update_fields=["sarraf_account_number", "sarraf_account_holder", "updated_at"])

    # ── فاکتور فروش + ردیف‌های تسویه ───────────────────────────────────
    # کسر موجودی از طریق رزروهای سفارش مدیریت می‌شود — deduct_from_inventory صدا زده نمی‌شود.
    from apps.accounting.models import SaleInvoice, SaleItem, SettlementLine

    confirm_date = timezone.now().date()
    invoice = SaleInvoice.objects.create(
        source=SaleInvoice.InvoiceSource.ORDER,
        status=SaleInvoice.Status.CONFIRMED,
        order=order,
        customer=order.user,
        customer_name=order.user.get_full_name(),
        customer_phone=order.user.phone,
        settlement=SaleInvoice.Settlement.CASH,
        due_date=None,
        created_by=staff,
    )
    for item in items:
        SaleItem.objects.create(
            invoice=invoice,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.confirmed_unit_price or item.unit_price,
        )

    # گروه‌بندی اقلام بر اساس نحوه تسویه — برای هر نوع یک ردیف تسویه
    totals_by_type = {}
    for item in items:
        price = item.confirmed_unit_price or item.unit_price
        totals_by_type[item.settlement_type] = (
            totals_by_type.get(item.settlement_type, 0) + price * item.quantity
        )
    for st, amount in totals_by_type.items():
        SettlementLine.objects.create(
            invoice=invoice,
            settlement_type=st,
            amount=amount,
            due_date=settlement_due_for(st, confirm_date),
        )

    # پیامک به مشتری (مرحله ۴)
    notify_inquiry_confirmed(order)
    from apps.notifications.services import notify_order_status_sms, notify_account_info_sms
    notify_order_status_sms(order)
    # پیامک اطلاعات حساب صراف برای پرداخت اقلام نقدی
    if has_cash_item and order.sarraf_account_number:
        notify_account_info_sms(
            order.user.phone, order.user.get_full_name(),
            order.sarraf_account_number, order.sarraf_account_holder,
            amount=order.confirmed_amount or order.total_amount,
            user=order.user, order=order,
        )

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

    # کسر موجودی واقعی + ثبت کاردکس (الگوی همان _record_warehouse_outflow حسابداری)
    from apps.inventory.models import StockMovement, Warehouse
    warehouse = (
        Warehouse.objects.filter(is_public=True, is_active=True).first()
        or Warehouse.objects.filter(is_active=True).first()
    )
    for item in order.items.select_related("variant").all():
        item.variant.deduct_stock(item.quantity)
        if warehouse is not None:
            try:
                StockMovement.record(
                    warehouse=warehouse,
                    variant=item.variant,
                    movement_type=StockMovement.MovementType.SALE,
                    quantity=-item.quantity,
                    unit_price=int(item.confirmed_unit_price or item.unit_price),
                    reference=order.order_number,
                    note=f"فروش پس از پرداخت سفارش {order.order_number}",
                )
            except Exception as exc:
                logger.warning(f"[INVENTORY] ثبت کاردکس فروش سفارش {order.order_number} ناموفق: {exc}")
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

    # اطلاع‌رسانی نزدیکی به آستانه ارتقای سطح باشگاه (best-effort)
    profile = getattr(order.user, "profile", None)
    if profile is not None:
        from apps.users.services import maybe_notify_near_tier
        try:
            maybe_notify_near_tier(profile)
        except Exception as e:
            logger.exception(f"[CLUB] خطا در بررسی آستانه سطح برای سفارش {order.order_number}: {e}")

    # فاکتور فروش فقط بعد از پرداخت موفق ساخته و همان لحظه تسویه می‌شود
    # (سفارش‌های تأییدشده توسط ادمین از قبل فاکتور دارند؛ سفارش‌های تأیید خودکار نه)
    from apps.accounting.services import settle_single_invoice
    invoice = getattr(order, "sale_invoice", None)
    if invoice is None:
        invoice = _create_sale_invoice_for_order(order, created_by=order.user)
    if invoice.remaining_amount > 0:
        settle_single_invoice(
            invoice, invoice.remaining_amount,
            date=timezone.localdate(), method="online",
            reference=str(ref_id),
            note=f"پرداخت آنلاین سفارش {order.order_number}",
        )

    notify_order_paid(order)
    from apps.notifications.services import notify_order_status_sms
    notify_order_status_sms(order)
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
    from apps.notifications.services import notify_order_status_sms
    notify_order_status_sms(order)
    logger.info(f"[ORDER] Cancelled: {order.order_number} | reason: {reason}")
    return order


# ─── Settlement reminders ──────────────────────────────────────────────────────

def due_settlements_queryset():
    """سفارش‌هایی که حداقل یک قلم اعتباری سررسیدرسیده دارند و هنوز تسویه/لغو نشده‌اند.
    علاوه بر منطق per-item قدیمی، سفارش‌هایی هم شامل می‌شوند که ردیف تسویهٔ
    فعال فاکتور فروششان سررسید رسیده و هنوز مانده دارد."""
    from django.db.models import Q, Sum, F
    today = timezone.now().date()
    credit_types = [Order.Settlement.CREDIT, Order.Settlement.MONTH1, Order.Settlement.MONTH2]
    closed_statuses = [
        Order.Status.PAID, Order.Status.CANCELLED,
        Order.Status.REFUNDED, Order.Status.REJECTED,
    ]

    base_filter = (
        Q(items__settlement_type__in=credit_types, items__settlement_due_date__lte=today)
        | Q(settlement_type__in=credit_types, settlement_due_date__lte=today)
    )

    # ردیف‌های تسویه فعالِ سررسیدرسیده با مانده > ۰ (مانده = amount − Σ allocations)
    # نقدی: روز صدور سررسید حساب نمی‌شود — از فردای صدور فاکتور یادآوری می‌رود.
    # اعتباری: از خود روز موعد سررسید حساب می‌شود.
    from apps.accounting.models import SettlementLine
    due_line_order_ids = (
        SettlementLine.objects
        .filter(is_active=True)
        .filter(
            Q(settlement_type="cash", due_date__lt=today)
            | Q(settlement_type__in=["credit", "month1", "month2"], due_date__lte=today)
        )
        .exclude(invoice__status="cancelled")
        .exclude(invoice__order__isnull=True)
        .annotate(paid=Sum("allocations__amount"))
        .filter(Q(paid__isnull=True) | Q(amount__gt=F("paid")))
        .values_list("invoice__order_id", flat=True)
    )

    return Order.objects.filter(
        base_filter | Q(pk__in=due_line_order_ids)
    ).exclude(status__in=closed_statuses).distinct()


def due_items(order):
    """اقلام سررسیدرسیده یک سفارش (برای متن هشدار)."""
    today = timezone.now().date()
    return order.items.filter(
        settlement_due_date__lte=today,
    ).exclude(settlement_type=Order.Settlement.CASH)


def send_due_settlement_reminders() -> int:
    """
    ارسال هشدار سررسید تسویه به مشتری و ادمین — برای هر سفارش روزی حداکثر یک بار.
    هم از کران (management command) و هم به‌صورت تنبل از بج‌های ادمین صدا زده می‌شود.
    """
    from apps.notifications.models import NotificationLog
    from apps.notifications.services import notify_settlement_due

    today = timezone.now().date()
    sent = 0
    for order in due_settlements_queryset():
        already = NotificationLog.objects.filter(
            order=order,
            subject__startswith="یادآوری موعد تسویه",
            created_at__date=today,
        ).exists()
        if already:
            continue
        try:
            notify_settlement_due(order, due_items(order))
            sent += 1
        except Exception as e:
            logger.error(f"[SETTLEMENT] reminder failed for {order.order_number}: {e}")
    return sent


def apply_customer_credit(user, actor=None) -> int:
    """
    بستانکاری نقدی مشتری (اضافه‌واریزی‌های قبلی) را به روش FIFO به فاکتورهای
    باز او تخصیص می‌دهد و فاکتور/سفارش تسویه‌شده را می‌بندد.
    منطق اصلی در apps.accounting.services.settle_customer_fifo است.
    → مبلغ اعمال‌شده (ریال)
    """
    profile = getattr(user, "profile", None)
    credit = int(profile.payment_credit_irr or 0) if profile else 0
    if not credit:
        return 0

    from apps.accounting.services import settle_customer_fifo

    # اعتبار را صفر می‌کنیم و به سرویس می‌دهیم — مازادِ استفاده‌نشده را خودش
    # دوباره به همان بستانکاری برمی‌گرداند
    profile.payment_credit_irr = 0
    profile.save(update_fields=["payment_credit_irr", "updated_at"])
    result = settle_customer_fifo(
        user, credit,
        date=timezone.now().date(), actor=actor, method="transfer",
        note="تخصیص خودکار از بستانکاری مشتری (اضافه‌واریزی قبلی)",
    )
    applied = credit - result["leftover"]
    if applied:
        logger.info(f"[CREDIT] {applied:,} ریال از بستانکاری {user.phone} به بدهی‌های باز تخصیص یافت")
    return applied
