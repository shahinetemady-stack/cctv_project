"""
apps/notifications/services.py
────────────────────────────────
Notification service — فقط ایمیل فعلاً.
پیامک بعداً اضافه می‌شود.

توابع:
  send_admin_email(subject, message, order)  → ایمیل به ادمین
  notify_inquiry_received(order)             → ایمیل به ادمین هنگام ثبت استعلام
  notify_inquiry_confirmed(order)            → ایمیل به مشتری هنگام تأیید
  notify_order_paid(order)                   → ایمیل به مشتری هنگام پرداخت
  notify_order_cancelled(order)              → ایمیل به مشتری هنگام کنسل
  notify_low_stock(variant)                  → ایمیل هشدار موجودی کم به ادمین
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
            recipient_address=recipient_address,
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
