def user_label(u):
    """نام نمایشی کاربر: نام کامل، در غیر این صورت موبایل"""
    if not u:
        return ''
    return (u.get_full_name() or getattr(u, 'phone', '') or str(u))


def audit_row(obj):
    """ردیف آماده ردیابی برای خروجی API — ثبت‌کننده و آخرین ویرایش‌کننده"""
    return {
        "created_by": user_label(getattr(obj, 'created_by', None)),
        "created_at": obj.created_at.strftime('%Y-%m-%d %H:%M') if getattr(obj, 'created_at', None) else '',
        "updated_by": user_label(getattr(obj, 'updated_by', None)),
        "updated_at": obj.updated_at.strftime('%Y-%m-%d %H:%M') if getattr(obj, 'updated_at', None) else '',
    }
