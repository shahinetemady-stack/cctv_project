"""
apps/publisher/services/telegram.py
────────────────────────────────────
انتشار در تلگرام از طریق Bot API.

api.telegram.org از سرور ایران در دسترس نیست؛ درخواست‌ها از یک رله روی
مینی‌PC عبور می‌کنند که مسیر /bot<token>/<method> را عیناً به تلگرام
پراکسی می‌کند. آدرس رله و توکن آن از env خوانده می‌شود:
  PUBLISHER_TG_RELAY_URL  (پیش‌فرض http://127.0.0.1:3298/tg)
  PUBLISHER_RELAY_TOKEN   (هدر X-Relay-Token)

اعتبارنامه: {"bot_token": "..."}
"""

import requests
from decouple import config

from .base import BaseMessengerService, PublishError


class TelegramService(BaseMessengerService):
    slug = "telegram"

    def _base_url(self) -> str:
        relay = config("PUBLISHER_TG_RELAY_URL", default="http://127.0.0.1:3298/tg")
        token = self.credential.credentials.get("bot_token", "")
        if not token:
            raise PublishError("توکن ربات تلگرام پیکربندی نشده است")
        return f"{relay.rstrip('/')}/bot{token}"

    def _headers(self) -> dict:
        return {"X-Relay-Token": config("PUBLISHER_RELAY_TOKEN", default="")}

    def _parse_response(self, resp) -> dict:
        try:
            data = resp.json()
        except ValueError:
            raise PublishError(f"پاسخ نامعتبر تلگرام: {resp.text[:300]}")
        if not data.get("ok"):
            raise PublishError(data.get("description") or "خطای نامشخص تلگرام")
        return data

    def publish(self, post) -> dict:
        chat_id = self.credential.chat_id
        if not chat_id:
            raise PublishError("شناسه کانال/چت مقصد برای تلگرام تنظیم نشده است")
        caption = self._caption(post)
        url = self._base_url()

        if post.video:
            with open(post.video.path, "rb") as fh:
                data = self._parse_response(requests.post(
                    f"{url}/sendVideo",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"video": fh},
                    headers=self._headers(),
                    timeout=30,
                ))
        elif post.image:
            with open(post.image.path, "rb") as fh:
                data = self._parse_response(requests.post(
                    f"{url}/sendPhoto",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"photo": fh},
                    headers=self._headers(),
                    timeout=30,
                ))
        else:
            data = self._parse_response(requests.post(
                f"{url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": caption,
                    "disable_web_page_preview": False,
                },
                headers=self._headers(),
                timeout=30,
            ))

        message_id = str((data.get("result") or {}).get("message_id", "")) or None
        return {"external_message_id": message_id, "raw": data}
