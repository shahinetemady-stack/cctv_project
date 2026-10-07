"""
apps/publisher/services/bale.py
────────────────────────────────
انتشار در بله از طریق Bot API سازگار با تلگرام:
  https://tapi.bale.ai/bot<token>/<method>
مستقیم و بدون رله — دقیقاً همان منطق sendMessage/sendPhoto/sendVideo تلگرام.

اعتبارنامه: {"bot_token": "..."}
"""

import requests

from .base import BaseMessengerService, PublishError

BASE_URL = "https://tapi.bale.ai"


class BaleService(BaseMessengerService):
    slug = "bale"

    def _base_url(self) -> str:
        token = self.credential.credentials.get("bot_token", "")
        if not token:
            raise PublishError("توکن ربات بله پیکربندی نشده است")
        return f"{BASE_URL}/bot{token}"

    def _parse_response(self, resp) -> dict:
        try:
            data = resp.json()
        except ValueError:
            raise PublishError(f"پاسخ نامعتبر بله: {resp.text[:300]}")
        if not data.get("ok"):
            raise PublishError(data.get("description") or "خطای نامشخص بله")
        return data

    def publish(self, post) -> dict:
        chat_id = self.credential.chat_id
        if not chat_id:
            raise PublishError("شناسه کانال/چت مقصد برای بله تنظیم نشده است")
        caption = self._caption(post)
        url = self._base_url()

        if post.video:
            with open(post.video.path, "rb") as fh:
                data = self._parse_response(requests.post(
                    f"{url}/sendVideo",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"video": fh},
                    timeout=30,
                ))
        elif post.image:
            with open(post.image.path, "rb") as fh:
                data = self._parse_response(requests.post(
                    f"{url}/sendPhoto",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"photo": fh},
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
                timeout=30,
            ))

        message_id = str((data.get("result") or {}).get("message_id", "")) or None
        return {"external_message_id": message_id, "raw": data}
