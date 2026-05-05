"""
apps/users/permissions.py
──────────────────────────
Custom DRF permission classes.

IsPartner        → همکار تأیید شده توسط ادمین
IsPartnerOrAdmin → همکار یا ادمین
IsOwnerOrAdmin   → صاحب منبع یا ادمین
IsAdminOrReadOnly → ادمین: همه | بقیه: فقط خواندن
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsPartner(BasePermission):
    """فقط مشتریان همکار تأیید شده — استعلام و قیمت همکار."""
    message = "این بخش فقط برای مشتریان همکار تأیید شده است."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_partner
        )


class IsPartnerOrAdmin(BasePermission):
    message = "دسترسی فقط برای همکاران تأیید شده یا ادمین."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.is_partner or request.user.is_staff


class IsOwnerOrAdmin(BasePermission):
    message = "فقط صاحب این منبع یا ادمین دسترسی دارد."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        return obj == request.user


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


# نگه داشتیم برای backward compat (orders/views.py از این import می‌کند)
IsVerifiedUser = IsPartner
