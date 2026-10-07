from django.utils import timezone


def user_label(u):
    """نام نمایشی کاربر: نام کامل، در غیر این صورت موبایل"""
    if not u:
        return ''
    return (u.get_full_name() or getattr(u, 'phone', '') or str(u))


def iso_local(dt):
    """ISO 8601 با آفست تهران — بدون آفست، مرورگر رشته را در منطقهٔ زمانیِ خودِ
    دستگاه تفسیر می‌کند و ساعت نمایشی جابه‌جا می‌شود."""
    return timezone.localtime(dt).isoformat(timespec='minutes') if dt else ''


def audit_row(obj):
    """ردیف آماده ردیابی برای خروجی API — ثبت‌کننده و آخرین ویرایش‌کننده"""
    return {
        "created_by": user_label(getattr(obj, 'created_by', None)),
        "created_at": iso_local(getattr(obj, 'created_at', None)),
        "updated_by": user_label(getattr(obj, 'updated_by', None)),
        "updated_at": iso_local(getattr(obj, 'updated_at', None)),
    }
