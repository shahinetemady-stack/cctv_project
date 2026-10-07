"""
apps/publisher/services/rubika.py
──────────────────────────────────
انتشار در روبیکا از طریق Bot API رسمی:
  POST https://botapi.rubika.ir/v3/{bot_token}/sendMessage
  بدنه JSON: {"chat_id": ..., "text": ...}
  پاسخ: {"status": "OK", "data": {...}} — هر وضعیت غیر OK خطا محسوب می‌شود.

ارسال فایل (تصویر/ویدیو) در این نسخه ساده‌سازی شده: اگر پست مدیا داشته باشد،
ابتدا تلاش می‌کنیم با متد requestSendFile/uploadFile که در اسناد روبیکا آمده
فایل را آپلود کنیم؛ چون این بخش API پایدار و مستند نیست، در صورت هر شکلی از
پاسخ نامشخص، به‌جای فایل یک یادداشت به انتهای متن اضافه می‌شود.

اعتبارنامه: {"bot_token": "..."}
"""

import requests

from .base import BaseMessengerService, PublishError

BASE_URL = "https://botapi.rubika.ir/v3"


class RubikaService(BaseMessengerService):
    slug = "rubika"

    def _token(self) -> str:
        token = self.credential.credentials.get("bot_token", "")
        if not token:
            raise PublishError("توکن ربات روبیکا پیکربندی نشده است")
        return token

    def _parse(self, resp) -> dict:
        try:
            data = resp.json()
        except ValueError:
            raise PublishError(f"پاسخ نامعتبر روبیکا: {resp.text[:300]}")
        if not isinstance(data, dict) or data.get("status") != "OK":
            raise PublishError(f"خطای روبیکا: {resp.text[:300]}")
        return data

    def publish(self, post) -> dict:
        chat_id = self.credential.chat_id
        if not chat_id:
            raise PublishError("شناسه کانال/چت مقصد برای روبیکا تنظیم نشده است")

        text = self._caption(post)
        if post.video or post.image:
            # ارسال فایل در Bot API روبیکا پایدار/مستند نیست — فعلاً فقط متن
            # ارسال می‌شود و به مخاطب اطلاع داده می‌شود مدیا روی لینک/سایت است.
            text += "\n\n(این پست دارای تصویر/ویدیو است — برای مشاهده به لینک مراجعه کنید)"

        data = self._parse(requests.post(
            f"{BASE_URL}/{self._token()}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        ))

        message_id = None
        payload = data.get("data")
        if isinstance(payload, dict):
            message_id = payload.get("message_id") or payload.get("messageId")
        return {"external_message_id": str(message_id) if message_id else None, "raw": data}
