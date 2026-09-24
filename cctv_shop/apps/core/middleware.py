import threading

_state = threading.local()


def set_current_user(user):
    _state.user = user


def get_current_user():
    return getattr(_state, "user", None)


class CurrentUserMiddleware:
    """کاربر جاری را در thread-local نگه می‌دارد تا مدل‌ها در save() به آن دسترسی داشته باشند."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        # پروژه فقط با JWT احراز می‌کند و JWT در لایه DRF (بعد از میدل‌ور) خوانده می‌شود؛
        # بدون این fallback، کاربر API همیشه ناشناس است و created_by/updated_by خالی می‌ماند
        if not (user and user.is_authenticated):
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                auth = JWTAuthentication().authenticate(request)
                if auth:
                    user = auth[0]
            except Exception:
                user = None
        set_current_user(user if user and user.is_authenticated else None)
        try:
            return self.get_response(request)
        finally:
            set_current_user(None)
