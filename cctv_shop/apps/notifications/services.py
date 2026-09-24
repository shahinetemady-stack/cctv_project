"""
apps/notifications/services.py
────────────────────────────────
Notification service — ایمیل + پیامک (sms.ir).

توابع ایمیل:
  send_admin_email(subject, message, order)  → ایمیل به ادمین
  notify_inquiry_received(order)             → ایمیل به ادمین هنگام ثبت استعلام
  notify_inquiry_confirmed(order)            → ایمیل به مشتری هنگام تأیید
  notify_order_paid(order)                   → ایمیل به مشتری هنگام پرداخت
  notify_order_cancelled(order)              → ایمیل به مشتری هنگام کنسل
  notify_low_stock(variant)                  → ایمیل هشدار موجودی کم به ادمین

توابع پیامک (قالب‌های Verify از تنظیمات پیامک در دیتابیس):
  notify_order_status_sms(order)             → تغییر وضعیت سفارش
  notify_payment_reminder_sms(line)          → یادآوری سررسید بدهی
  notify_tier_change_sms(phone, name, tier)  → تغییر سطح همکاری
  notify_partner_approved_sms(user)          → تأیید درخواست همکاری
  notify_invoice_confirmed_sms(invoice)      → تأیید فاکتور فروش
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def _log(channel, recipient_type, recipient_address, message,
         status, subject="", order=None, user=None,
         provider_response="", error_message=""):
    """ثبت هر ارسال در NotificationLog."""
    try:
        from apps.notifications.models import NotificationLog
        NotificationLog.objects.create(
            channel=channel,
            recipient_type=recipient_type,
            recipient_address=recipient_address or "",
            subject=subject,
            message=message,
            status=status,
            sent_at=timezone.now() if status == "sent" else None,
            provider_response=provider_response,
            error_message=error_message,
            order=order,
            user=user,
        )
    except Exception as e:
        logger.error(f"[LOG] NotificationLog write failed: {e}")


# ─── Email ────────────────────────────────────────────────────────────────────

def send_admin_email(subject: str, message: str, order=None) -> bool:
    """ارسال ایمیل هشدار / اطلاع‌رسانی به ادمین."""
    admin_email = getattr(settings, "ADMIN_EMAIL", "")
    if not admin_email:
        logger.warning("[EMAIL] ADMIN_EMAIL not configured.")
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER or "noreply@cctvshop.ir",
            recipient_list=[admin_email],
            fail_silently=False,
        )
        _log("email", "admin", admin_email, message, "sent",
             subject=subject, order=order)
        logger.info(f"[EMAIL] Admin email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL] Failed: {e}")
        _log("email", "admin", admin_email, message, "failed",
             subject=subject, order=order, error_message=str(e))
        return False


def send_user_email(to_email: str, subject: str, message: str,
                    order=None, user=None) -> bool:
    """ارسال ایمیل به کاربر."""
    if not to_email:
        # کاربر ایمیل ندارد — بدون لاگِ خراب‌کننده تراکنش فقط رد شود
        logger.warning(f"[EMAIL] skipped (no recipient): {subject}")
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER or "noreply@cctvshop.ir",
            recipient_list=[to_email],
            fail_silently=False,
        )
        _log("email", "user", to_email, message, "sent",
             subject=subject, order=order, user=user)
        return True
    except Exception as e:
        logger.error(f"[EMAIL] User email failed to {to_email}: {e}")
        _log("email", "user", to_email, message, "failed",
             subject=subject, order=order, user=user, error_message=str(e))
        return False


# ─── Order notifications ──────────────────────────────────────────────────────

def notify_inquiry_received(order) -> None:
    """ایمیل به ادمین هنگام ثبت سفارش استعلامی."""
    send_admin_email(
        subject=f"استعلام جدید #{order.order_number}",
        message=(
            f"سفارش استعلامی جدید ثبت شد:\n\n"
            f"شماره: {order.order_number}\n"
            f"مشتری: {order.user.email}\n"
            f"تعداد آیتم: {order.items.count()}\n\n"
            f"برای بررسی وارد پنل ادمین شوید."
        ),
        order=order,
    )


def notify_inquiry_confirmed(order) -> None:
    """ایمیل به مشتری همکار هنگام تأیید سفارش."""
    deadline = ""
    if order.payment_deadline:
        deadline = order.payment_deadline.strftime("%Y/%m/%d %H:%M")

    send_user_email(
        to_email=order.user.email,
        subject=f"سفارش #{order.order_number} تأیید شد",
        message=(
            f"سفارش شما تأیید شد.\n\n"
            f"مبلغ نهایی: {order.confirmed_amount:,} تومان\n"
            f"لینک پرداخت: {order.payment_link}\n"
            f"مهلت پرداخت: {deadline}\n\n"
            f"پس از انقضای مهلت، رزرو موجودی آزاد می‌شود."
        ),
        order=order,
        user=order.user,
    )


def notify_order_paid(order) -> None:
    """ایمیل تأیید پرداخت."""
    send_user_email(
        to_email=order.user.email,
        subject=f"پرداخت سفارش #{order.order_number} موفق بود",
        message=(
            f"پرداخت شما با موفقیت انجام شد.\n\n"
            f"شماره سفارش: {order.order_number}\n"
            f"کد پیگیری: {order.payment_ref_id}\n\n"
            f"ممنون از خرید شما."
        ),
        order=order,
        user=order.user,
    )


def notify_order_cancelled(order) -> None:
    """ایمیل اطلاع از کنسل شدن."""
    send_user_email(
        to_email=order.user.email,
        subject=f"سفارش #{order.order_number} لغو شد",
        message=(
            f"سفارش {order.order_number} به دلیل انقضای مهلت پرداخت لغو شد.\n"
            f"برای سفارش مجدد به سایت مراجعه کنید."
        ),
        order=order,
        user=order.user,
    )


def notify_order_rejected(order, reason: str = "") -> None:
    """ایمیل به مشتری هنگام رد پیش‌فاکتور توسط ادمین."""
    send_user_email(
        to_email=order.user.email,
        subject=f"پیش‌فاکتور #{order.order_number} رد شد",
        message=(
            f"متأسفانه پیش‌فاکتور شما رد شد.\n\n"
            f"شماره سفارش: {order.order_number}\n"
            f"دلیل رد: {reason}\n\n"
            f"برای اطلاعات بیشتر با فروشگاه تماس بگیرید."
        ),
        order=order,
        user=order.user,
    )


def notify_low_stock(variant) -> None:
    """ایمیل هشدار موجودی کم + ثبت StockAlert."""
    from django.conf import settings as s
    from apps.inventory.models import StockAlert

    threshold = getattr(s, "LOW_STOCK_THRESHOLD", 5)
    available = variant.available_stock

    alert, created = StockAlert.objects.get_or_create(
        variant=variant,
        is_resolved=False,
        defaults={"stock_at_alert": available, "threshold": threshold},
    )

    if created or not alert.email_sent:
        sent = send_admin_email(
            subject=f"⚠️ موجودی کم: {variant.sku}",
            message=(
                f"موجودی محصول به سطح هشدار رسید:\n\n"
                f"محصول: {variant.product.name}\n"
                f"SKU: {variant.sku}\n"
                f"موجودی: {available} عدد (آستانه: {threshold})\n\n"
                f"لطفاً موجودی را بروزرسانی کنید."
            ),
        )
        if sent:
            alert.email_sent = True
            alert.email_sent_at = timezone.now()
            alert.save(update_fields=["email_sent", "email_sent_at", "updated_at"])


def notify_settlement_due(order, items=None) -> None:
    """هشدار سررسید تسویه — ایمیل به مشتری و ادمین (تاریخ‌ها شمسی، با فهرست اقلام سررسیدرسیده)."""
    from apps.core.utils import jalali_date

    if items is not None and len(items):
        lines = [
            f"• {it.variant.product.name} × {it.quantity} — {it.get_settlement_type_display()} — موعد: {jalali_date(it.settlement_due_date)}"
            for it in items
        ]
        items_text = "\n".join(lines)
    else:
        due = jalali_date(order.settlement_due_date) if order.settlement_due_date else "—"
        items_text = f"موعد تسویه: {due}"

    send_user_email(
        to_email=order.user.email,
        subject=f"یادآوری موعد تسویه سفارش #{order.order_number}",
        message=(
            f"موعد تسویه اقلام زیر از سفارش شما فرا رسیده است:\n\n"
            f"شماره سفارش: {order.order_number}\n"
            f"{items_text}\n\n"
            f"لطفاً جهت تسویه با فروشگاه تماس بگیرید."
        ),
        order=order,
        user=order.user,
    )
    send_admin_email(
        subject=f"سررسید تسویه سفارش #{order.order_number}",
        message=(
            f"موعد تسویه اقلام زیر رسیده است:\n\n"
            f"شماره: {order.order_number}\n"
            f"مشتری: {order.user}\n"
            f"{items_text}\n"
        ),
        order=order,
    )


def notify_receipt_approved(receipt) -> None:
    """ایمیل به مشتری هنگام تأیید فیش واریزی."""
    send_user_email(
        to_email=receipt.customer.email,
        subject=f"فیش واریزی سفارش #{receipt.order.order_number} تأیید شد",
        message=(
            f"فیش واریزی شما تأیید و به تسویه‌های باز شما تخصیص یافت.\n\n"
            f"شماره سفارش: {receipt.order.order_number}\n"
            f"مبلغ: {receipt.amount:,} ریال\n"
            f"تاریخ واریز: {receipt.paid_at}\n\n"
            f"ممنون از همراهی شما."
        ),
        order=receipt.order,
        user=receipt.customer,
    )


def notify_receipt_rejected(receipt, reason: str = "") -> None:
    """ایمیل به مشتری هنگام رد فیش واریزی."""
    send_user_email(
        to_email=receipt.customer.email,
        subject=f"فیش واریزی سفارش #{receipt.order.order_number} رد شد",
        message=(
            f"متأسفانه فیش واریزی شما رد شد.\n\n"
            f"شماره سفارش: {receipt.order.order_number}\n"
            f"مبلغ: {receipt.amount:,} ریال\n"
            f"دلیل رد: {reason}\n\n"
            f"لطفاً پس از بررسی، فیش صحیح را مجدداً بارگذاری کنید."
        ),
        order=receipt.order,
        user=receipt.customer,
    )


# ─── SMS (sms.ir) ─────────────────────────────────────────────────────────────
# همه توابع best-effort‌اند: خطاها لاگ می‌شوند ولی هرگز raise نمی‌کنند
# تا جریان اصلی (ثبت سفارش، تأیید فاکتور و...) مختل نشود.

def _notify_sms(phone, template_kind, params, *, enabled=True,
                user=None, order=None, subject="") -> bool:
    """ارسال پیامک Verify + لاگ. اگر قالب تنظیم نشده یا غیرفعال است، ساکت رد می‌شود."""
    try:
        from apps.notifications.sms import send_verify, get_template_id
        template_id = get_template_id(template_kind)
        if not enabled or not template_id or not phone:
            return False
        ok = send_verify(phone, template_id, params)
        _log(
            channel="sms",
            recipient_type="user",
            recipient_address=phone,
            subject=subject or template_kind,
            message=str(params),
            status="sent" if ok else "failed",
            user=user,
            order=order,
            error_message="" if ok else "sms.ir send failed",
        )
        return ok
    except Exception as e:
        logger.exception(f"[SMS] خطا در اطلاع‌رسانی {template_kind} به {phone}: {e}")
        return False


def notify_order_status_sms(order) -> None:
    """پیامک به مشتری هنگام تغییر وضعیت سفارش."""
    from apps.notifications.sms import get_sms_settings
    try:
        phone = getattr(order.user, "phone", "") or ""
        _notify_sms(
            phone, "order_status",
            {"ORDERID": order.order_number, "STATUS": order.get_status_display()},
            enabled=get_sms_settings().order_status_enabled,
            user=order.user, order=order,
            subject=f"تغییر وضعیت سفارش #{order.order_number}",
        )
    except Exception as e:
        logger.exception(f"[SMS] خطا در پیامک وضعیت سفارش {getattr(order, 'order_number', '?')}: {e}")


def notify_payment_reminder_sms(line) -> None:
    """یادآوری سررسید بدهی (SettlementLine سررسیدگذشته)."""
    from apps.notifications.sms import get_sms_settings
    inv = line.invoice
    phone = (getattr(inv.customer, "phone", "") or "") or (inv.customer_phone or "")
    try:
        import jdatetime
        due = jdatetime.date.fromgregorian(date=line.due_date).strftime("%Y/%m/%d")
    except Exception:
        due = str(line.due_date)
    _notify_sms(
        phone, "payment_reminder",
        {"NAME": inv.customer_name or "مشتری", "AMOUNT": f"{line.remaining_amount:,}", "DATE": due},
        enabled=get_sms_settings().payment_reminder_enabled,
        user=inv.customer,
        subject=f"payment_reminder:{line.id}",
    )


def notify_tier_change_sms(phone, name, tier_display) -> None:
    """پیامک تغییر سطح همکاری (گلد/پلاتینیوم/...)."""
    from apps.notifications.sms import get_sms_settings
    _notify_sms(
        phone, "tier_change",
        {"NAME": name or "مشتری", "TIER": tier_display},
        enabled=get_sms_settings().tier_change_enabled,
        subject="تغییر سطح همکاری",
    )


def notify_near_tier_sms(phone, name, tier_display, remaining_display) -> None:
    """پیامک «نزدیک به آستانه ارتقای سطح» — باقی‌مانده خرید تا سطح بعدی."""
    from apps.notifications.sms import get_sms_settings
    _notify_sms(
        phone, "near_tier",
        {"NAME": name or "مشتری", "TIER": tier_display, "REMAINING": remaining_display},
        enabled=get_sms_settings().near_tier_enabled,
        subject="نزدیک به آستانه ارتقای سطح",
    )


def notify_partner_request_sms(user) -> None:
    """پیامک «درخواست همکاری ثبت شد» — بلافاصله بعد از ثبت درخواست (در انتظار تأیید ادمین)."""
    from apps.notifications.sms import get_sms_settings
    name = f"{user.first_name} {user.last_name}".strip()
    _notify_sms(
        user.phone or "", "partner_request",
        {"NAME": name or "همکار"},
        enabled=get_sms_settings().partner_request_enabled,
        user=user,
        subject="ثبت درخواست همکاری",
    )


def notify_partner_approved_sms(user) -> None:
    """پیامک تأیید درخواست همکاری."""
    from apps.notifications.sms import get_sms_settings
    name = f"{user.first_name} {user.last_name}".strip()
    _notify_sms(
        user.phone or "", "partner_approved",
        {"NAME": name or "همکار"},
        enabled=get_sms_settings().partner_approved_enabled,
        user=user,
        subject="تأیید همکاری",
    )


def notify_invoice_confirmed_sms(inv) -> None:
    """پیامک تأیید فاکتور/پیش‌فاکتور فروش."""
    from apps.notifications.sms import get_sms_settings
    phone = (getattr(inv.customer, "phone", "") or "") or (inv.customer_phone or "")
    _notify_sms(
        phone, "invoice_confirmed",
        {"NAME": inv.customer_name or "مشتری", "NUMBER": inv.invoice_number},
        enabled=get_sms_settings().invoice_confirmed_enabled,
        user=inv.customer,
        subject=f"تأیید فاکتور {inv.invoice_number}",
    )


def notify_account_info_sms(phone, name, account_number, holder, amount=None, *, user=None, order=None) -> None:
    """پیامک اطلاعات حساب برای پرداخت (مبلغ + شماره حساب/کارت + نام صاحب حساب)."""
    from apps.notifications.sms import get_sms_settings
    _notify_sms(
        phone, "account_info",
        {"NAME": name or "مشتری", "ACCOUNT": account_number, "HOLDER": holder,
         "AMOUNT": f"{int(amount):,}" if amount else "—"},
        enabled=get_sms_settings().account_info_enabled,
        user=user, order=order,
        subject="اطلاعات حساب پرداخت",
    )


def notify_invoice_account_info_sms(inv) -> None:
    """ارسال اطلاعات حساب فروشگاه برای فاکتورهای دستی (فروش حضوری).
    حساب = اولین حساب بانکی ریالی فعال در حسابداری."""
    phone = (getattr(inv.customer, "phone", "") or "") or (inv.customer_phone or "")
    try:
        from apps.accounting.models import Account
        acc = (Account.objects.filter(is_active=True, account_type="bank", currency="IRR")
               .exclude(account_number="").first())
    except Exception:
        acc = None
    if acc is None:
        logger.warning("[SMS] اطلاعات حساب پرداخت: هیچ حساب بانکی فعالی تعریف نشده است")
        return
    notify_account_info_sms(
        phone, inv.customer_name, acc.account_number, acc.name,
        amount=inv.total_amount,
        user=inv.customer,
    )
