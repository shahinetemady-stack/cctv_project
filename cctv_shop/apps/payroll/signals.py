"""سیگنال‌های حقوق — ساخت خودکار طرف‌حساب برای پرسنل.

به محض کارمند شدن یک کاربر (is_staff) یا ساخت/ویرایش StaffProfile،
طرف‌حساب نوع «کارمند» ساخته و در UserProfile.linked_contact لینک می‌شود
تا پرداخت حقوق از صفحه دریافت و پرداخت و سند هزینه سر ماه بدون هیچ
کار دستی کار کنند.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


def _ensure_staff_contact(staff):
    if not staff.is_staff:
        return
    from .services import _staff_contact
    _staff_contact(staff)


@receiver(post_save, sender="users.User")
def user_saved(sender, instance, created, **kwargs):
    if instance.is_staff:
        _ensure_staff_contact(instance)


@receiver(post_save, sender="users.StaffProfile")
def staff_profile_saved(sender, instance, created, **kwargs):
    _ensure_staff_contact(instance.user)
