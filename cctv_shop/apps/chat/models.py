"""
apps/chat/models.py
───────────────────
چت مشتری ↔ پرسنل — سبک و بدون WebSocket (polling).
هر مشتری یک گفتگو دارد؛ پیام‌ها متن و/یا فایل (media/chat/) هستند که nginx مستقیم
سرو می‌کند. is_read یعنی «طرف مقابل» پیام را دیده است.
"""
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    customer   = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                    related_name="chat_conversation", verbose_name="مشتری")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name="assigned_chats",
                    verbose_name="اختصاص به پرسنل",
                    help_text="خالی = پشتیبانی عمومی — برای همه پرسنل نمایش داده می‌شود؛ "
                              "با تخصیص، فقط همان پرسنل (و سوپریوزر) می‌بیند")
    is_closed  = models.BooleanField(default=False, verbose_name="بسته شده",
                    help_text="با پیام جدید مشتری خودبه‌خود باز می‌شود")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_conversation"
        verbose_name = "گفتگو"
        verbose_name_plural = "گفتگوها"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"گفتگوی {self.customer}"


class ChatMessage(models.Model):
    conversation    = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                        related_name="messages", verbose_name="گفتگو")
    sender          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                        null=True, related_name="chat_messages", verbose_name="فرستنده")
    from_staff      = models.BooleanField(default=False, verbose_name="از طرف پرسنل")
    text            = models.TextField(blank=True, verbose_name="متن")
    attachment      = models.FileField(upload_to="chat/%Y/%m", null=True, blank=True,
                        verbose_name="پیوست")
    attachment_name = models.CharField(max_length=255, blank=True, verbose_name="نام فایل")
    is_read         = models.BooleanField(default=False, verbose_name="خوانده شده توسط طرف مقابل")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"
        verbose_name = "پیام چت"
        verbose_name_plural = "پیام‌های چت"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["conversation", "id"]),
            models.Index(fields=["from_staff", "is_read"]),
        ]

    def __str__(self):
        kind = "پرسنل" if self.from_staff else "مشتری"
        return f"[{kind}] {self.text[:40] or self.attachment_name}"
