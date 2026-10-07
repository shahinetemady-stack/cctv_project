"""
apps/publisher/services/base.py
────────────────────────────────
کلاس پایه سرویس‌های انتشار + استثنای PublishError.
همه سرویس‌ها با requests و timeout=30 کار می‌کنند؛ هندل فایل‌ها همیشه
با context manager باز و بسته می‌شوند.
"""


class PublishError(Exception):
    """خطای انتشار — پیام آن مستقیم در لاگ ذخیره و به کاربر نشان داده می‌شود."""


class BaseMessengerService:
    """قرارداد سرویس انتشار در یک پیام‌رسان."""

    slug = ""

    def __init__(self, credential):
        # credential: نمونه ChannelCredential (پلتفرم + اعتبارنامه رمزگشایی‌شده)
        self.credential = credential

    def publish(self, post) -> dict:
        """
        پست را منتشر می‌کند و {"external_message_id": str|None, "raw": dict}
        برمی‌گرداند. در شکست PublishError می‌اندازد.
        """
        raise NotImplementedError

    def _caption(self, post) -> str:
        """متن نهایی = متن محتوا + لینک (در صورت وجود)."""
        text = post.body or ""
        if post.link:
            text = f"{text}\n\n{post.link}" if text else post.link
        return text
