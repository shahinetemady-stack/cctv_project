"""
apps/publisher/services/whatsapp.py
────────────────────────────────────
انتشار در واتساپ از طریق WAHA (WhatsApp HTTP API).

WAHA یک سرویس self-hosted است که روی یک حساب واتساپ سوار می‌شود. چون
واتساپ IP ایرانی را محدود/مسدود می‌کند، WAHA باید روی VPS آمریکا اجرا
شود و از ایران فقط API آن صدا زده می‌شود.

تنظیمات env:
  PUBLISHER_WAHA_URL    مثل https://waha.example.com
  PUBLISHER_WAHA_TOKEN  کلید API (هدر X-Api-Key)

اعتبارنامه: {"session": "default"}  — نام سشن WAHA

اگر env تنظیم نشده باشد، انتشار با خطای مشخص شکست می‌خورد.
توجه: سروش (پیام‌رسان) API عمومی پایداری ندارد و فعلاً پشتیبانی نمی‌شود.
"""

import requests
from decouple import config

from .base import BaseMessengerService, PublishError


class WhatsAppService(BaseMessengerService):
    slug = "whatsapp"

    def publish(self, post) -> dict:
        waha_url = config("PUBLISHER_WAHA_URL", default="").rstrip("/")
        waha_token = config("PUBLISHER_WAHA_TOKEN", default="")
        if not waha_url or not waha_token:
            raise PublishError("واتساپ هنوز پیکربندی نشده است — نیازمند WAHA روی VPS آمریکا")

        chat_id = self.credential.chat_id
        if not chat_id:
            raise PublishError("شناسه کانال/چت مقصد برای واتساپ تنظیم نشده است")
        session = self.credential.credentials.get("session", "default")

        text = self._caption(post)
        if post.video or post.image:
            text += "\n\n(این پست دارای تصویر/ویدیو است — برای مشاهده به لینک مراجعه کنید)"

        resp = requests.post(
            f"{waha_url}/api/sendText",
            headers={"X-Api-Key": waha_token},
            json={"chatId": chat_id, "text": text, "session": session},
            timeout=30,
        )
        if not resp.ok:
            raise PublishError(f"خطای WAHA ({resp.status_code}): {resp.text[:300]}")

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text[:500]}
        message_id = None
        if isinstance(data, dict):
            # WAHA شناسه پیام را در id._serialized یا id برمی‌گرداند
            msg_id = data.get("id")
            if isinstance(msg_id, dict):
                message_id = msg_id.get("_serialized")
            elif msg_id:
                message_id = str(msg_id)
        return {"external_message_id": message_id, "raw": data}
