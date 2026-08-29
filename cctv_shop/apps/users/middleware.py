"""
apps/users/middleware.py — ثبت خودکار لاگ فعالیت‌ها.

رویکرد اصولی (Audit Middleware): به‌جای دست‌کاری تک‌تک ویوها، یک میدل‌ور مرکزی
همه درخواست‌های نوشتاری موفق API (POST/PATCH/PUT/DELETE) را با کاربر، مسیر،
متد و زمان ثبت می‌کند + رویدادهای ورود/خروج. خواندنی‌ها (GET) لاگ نمی‌شوند
تا حجم داده و نویز کنترل شود.
"""
import json
import logging

from .models import ActivityLog

logger = logging.getLogger(__name__)

METHOD_ACTION = {
    "POST": ActivityLog.Action.CREATE,
    "PATCH": ActivityLog.Action.UPDATE,
    "PUT": ActivityLog.Action.UPDATE,
    "DELETE": ActivityLog.Action.DELETE,
}
AUTH_PATHS = {
    "/api/users/auth/login": ActivityLog.Action.LOGIN,
    "/api/users/auth/logout": ActivityLog.Action.LOGOUT,
    "/api/users/auth/register": ActivityLog.Action.CREATE,
}
SKIP_PREFIXES = ("/api/users/auth/refresh",)


class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._maybe_log(request, response)
        except Exception as exc:  # لاگ هرگز نباید جلوی درخواست را بگیرد
            logger.warning(f"[ACTIVITY] خطا در ثبت لاگ: {exc}")
        return response

    def _maybe_log(self, request, response):
        path = request.path.rstrip("/")
        if not path.startswith("/api/") or path.startswith(SKIP_PREFIXES):
            return
        if not (200 <= response.status_code < 300):
            return

        user = request.user if request.user.is_authenticated else None

        if path in AUTH_PATHS:
            action = AUTH_PATHS[path]
            if action == ActivityLog.Action.LOGIN and user is None:
                user = self._user_from_body(request, response)
        elif request.method in METHOD_ACTION:
            if user is None:
                return
            action = METHOD_ACTION[request.method]
        else:
            return

        ActivityLog.objects.create(
            user=user, action=action, method=request.method,
            path=path, status=response.status_code,
        )

    @staticmethod
    def _user_from_body(request, response=None):
        """یافتن کاربر لاگین — اول از بدنه درخواست، fallback از بدنه پاسخ (user.id)."""
        from django.contrib.auth import get_user_model
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
            username = (body.get("username") or "").strip()
            if username:
                u = get_user_model().objects.filter(phone=username).first()
                if u:
                    return u
        except Exception:
            pass
        # fallback — پاسخ لاگین موفق کاربر را دارد
        try:
            data = json.loads(response.content.decode("utf-8"))
            uid = (data.get("user") or {}).get("id")
            if uid:
                return get_user_model().objects.filter(pk=uid).first()
        except Exception:
            pass
        return None
