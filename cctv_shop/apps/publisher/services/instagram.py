"""
apps/publisher/services/instagram.py
────────────────────────────────────
انتشار در اینستاگرام از طریق Graph API (Content Publishing).

graph.facebook.com به دلیل تحریم از سرور ایران در دسترس نیست؛ درخواست‌ها
از یک رله روی مینی‌PC عبور می‌کنند که مسیر /ig/<path> را عیناً به
graph.facebook.com پراکسی می‌کند. آدرس رله و توکن آن از env خوانده می‌شود:
  PUBLISHER_IG_RELAY_URL    (پیش‌فرض http://127.0.0.1:3297/ig)
  PUBLISHER_IG_RELAY_TOKEN  (هدر X-Relay-Token)

اعتبارنامه: {"access_token": "...", "ig_user_id": "..."}

جریان انتشار (API v21.0):
  ۱) ساخت کانتینر مدیا  POST /{ig_user_id}/media
  ۲) انتظار برای FINISHED  GET /{container_id}?fields=status_code,status
  ۳) انتشار              POST /{ig_user_id}/media_publish
مدیا باید از یک URL عمومی در دسترس باشد؛ فایل‌های MEDIA روی
https://doorbinkar.com/media/... توسط nginx سرو می‌شوند.
"""

import time

import requests
from decouple import config

from .base import BaseMessengerService, PublishError

API_VERSION = "v21.0"
SITE_BASE = "https://doorbinkar.com"
STATUS_MAX_TRIES = 10
STATUS_SLEEP_SECONDS = 6


class InstagramService(BaseMessengerService):
    slug = "instagram"

    def _relay_url(self) -> str:
        return config(
            "PUBLISHER_IG_RELAY_URL", default="http://127.0.0.1:3297/ig"
        ).rstrip("/")

    def _headers(self) -> dict:
        return {"X-Relay-Token": config("PUBLISHER_IG_RELAY_TOKEN", default="")}

    def _credentials(self) -> tuple:
        creds = self.credential.credentials
        access_token = creds.get("access_token", "")
        ig_user_id = creds.get("ig_user_id", "")
        if not access_token or not ig_user_id:
            raise PublishError("اعتبارنامه اینستاگرام (access_token / ig_user_id) پیکربندی نشده است")
        return access_token, ig_user_id

    def _parse_response(self, resp) -> dict:
        try:
            data = resp.json()
        except ValueError:
            raise PublishError(f"پاسخ نامعتبر اینستاگرام: {resp.text[:300]}")
        if resp.status_code >= 400 or "error" in data:
            err = data.get("error") or {}
            message = err.get("message") or f"خطای نامشخص اینستاگرام (HTTP {resp.status_code})"
            raise PublishError(message)
        return data

    def _caption(self, post) -> str:
        caption = super()._caption(post)
        if post.hashtags:
            caption = f"{caption}\n\n{post.hashtags}" if caption else post.hashtags
        return caption

    def _media_url(self, field) -> str:
        return f"{SITE_BASE}{field.url}"

    def _container_params(self, post) -> dict:
        """پارامترهای ساخت کانتینر بر اساس نوع محتوا و مدیا."""
        caption = self._caption(post)
        is_story = post.content_type == "story"
        if post.video:
            params = {"video_url": self._media_url(post.video)}
            if is_story:
                params["media_type"] = "STORIES"
            else:
                params.update({
                    "media_type": "REELS",
                    "caption": caption,
                    "share_to_feed": "true",
                })
        elif post.image:
            params = {"image_url": self._media_url(post.image)}
            if is_story:
                params["media_type"] = "STORIES"
            else:
                params["caption"] = caption
        else:
            raise PublishError("اینستاگرام بدون رسانه ممکن نیست")
        return params

    def _create_container(self, post, access_token, ig_user_id) -> str:
        params = self._container_params(post)
        params["access_token"] = access_token
        data = self._parse_response(requests.post(
            f"{self._relay_url()}/{API_VERSION}/{ig_user_id}/media",
            data=params,
            headers=self._headers(),
            timeout=30,
        ))
        container_id = data.get("id")
        if not container_id:
            raise PublishError("شناسه کانتینر از اینستاگرام دریافت نشد")
        return container_id

    def _wait_container(self, container_id, access_token) -> None:
        url = f"{self._relay_url()}/{API_VERSION}/{container_id}"
        for _ in range(STATUS_MAX_TRIES):
            data = self._parse_response(requests.get(
                url,
                params={"fields": "status_code,status", "access_token": access_token},
                headers=self._headers(),
                timeout=15,
            ))
            status = data.get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                detail = data.get("status") or status
                raise PublishError(f"پردازش مدیا در اینستاگرام ناموفق بود: {detail}")
            time.sleep(STATUS_SLEEP_SECONDS)
        raise PublishError("مهلت پردازش مدیا در اینستاگرام به پایان رسید")

    def _publish_container(self, container_id, access_token, ig_user_id) -> dict:
        return self._parse_response(requests.post(
            f"{self._relay_url()}/{API_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": access_token},
            headers=self._headers(),
            timeout=30,
        ))

    def publish(self, post) -> dict:
        access_token, ig_user_id = self._credentials()
        container_id = self._create_container(post, access_token, ig_user_id)
        self._wait_container(container_id, access_token)
        data = self._publish_container(container_id, access_token, ig_user_id)
        media_id = str(data.get("id", "")) or None
        return {"external_message_id": media_id, "raw": {"container_id": container_id, **data}}
