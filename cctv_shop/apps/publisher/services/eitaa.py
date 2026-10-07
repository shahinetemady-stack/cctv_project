"""
apps/publisher/services/eitaa.py
─────────────────────────────────
انتشار در ایتا.

ایتا API رسمی و عمومی برای ربات ندارد؛ این سرویس بر اساس یک گیت‌وی
شخص ثالث (مثل eitaayar.ir) پیاده‌سازی شده است — برای استفاده باید حساب
گیت‌وی داشته باشید و base_url و token آن را در اعتبارنامه قرار دهید.

اعتبارنامه: {"base_url": "https://eitaayar.ir/api", "token": "..."}
درخواست: POST {base_url}/{token}/sendMessage  JSON {"chat_id": ..., "text": ...}

توجه: شکل پاسخ این گیت‌وی‌ها یکسان نیست؛ هر پاسخ غیر-OK یا نامشخص با متن
خام به‌عنوان PublishError رد می‌شود.
"""

import requests

from .base import BaseMessengerService, PublishError


class EitaaService(BaseMessengerService):
    slug = "eitaa"

    def publish(self, post) -> dict:
        creds = self.credential.credentials
        base_url = (creds.get("base_url") or "").rstrip("/")
        token = creds.get("token") or ""
        if not base_url or not token:
            raise PublishError("گیت‌وی ایتا پیکربندی نشده است (base_url / token)")
        chat_id = self.credential.chat_id
        if not chat_id:
            raise PublishError("شناسه کانال/چت مقصد برای ایتا تنظیم نشده است")

        text = self._caption(post)
        if post.video or post.image:
            text += "\n\n(این پست دارای تصویر/ویدیو است — برای مشاهده به لینک مراجعه کنید)"

        resp = requests.post(
            f"{base_url}/{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        )

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text[:500]}
        # شکل پاسخ گیت‌وی‌ها متفاوت است — هر نشانه‌ای از شکست را خطا می‌دانیم
        if not resp.ok:
            raise PublishError(f"خطای گیت‌وی ایتا ({resp.status_code}): {resp.text[:300]}")
        if isinstance(data, dict) and data.get("ok") is False:
            raise PublishError(f"خطای گیت‌وی ایتا: {data}")

        message_id = None
        if isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, dict):
                message_id = result.get("message_id")
            message_id = message_id or data.get("message_id")
        return {"external_message_id": str(message_id) if message_id else None, "raw": data}
