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
        set_current_user(user if user and user.is_authenticated else None)
        try:
            return self.get_response(request)
        finally:
            set_current_user(None)
