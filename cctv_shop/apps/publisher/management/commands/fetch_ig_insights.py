"""
کامند دریافت آمار (اینسایت) پست‌های منتشرشده در اینستاگرام از Graph API.

برای هر PublishLog موفق اینستاگرام که external_message_id (شناسه مدیا) دارد،
متریک‌های reach/likes/comments/shares/saved/views از مسیر
  GET /v21.0/{media_id}/insights
خوانده و در ContentInsight ذخیره/به‌روز می‌شود. پاسخ خام کامل در raw نگه‌داری
می‌شود؛ نام‌های متریک ناشناخته (مثل total_interactions در نسخه‌های قدیمی API)
فقط در raw می‌مانند و نادیده گرفته نمی‌شوند.

پیش‌نیاز: توکن اینستاگرام باید اسکوپ instagram_manage_insights را داشته باشد؛
در غیر این صورت Graph API خطای permission برمی‌گردد و برای هر پست اخطار چاپ
می‌شود (اجرای کامند متوقف نمی‌شود).

تنظیمات رله همان env های InstagramService است:
  PUBLISHER_IG_RELAY_URL / PUBLISHER_IG_RELAY_TOKEN

مثال:
    python manage.py fetch_ig_insights
    python manage.py fetch_ig_insights --dry-run
"""

import requests
from decouple import config
from django.core.management.base import BaseCommand, CommandError

from ...models import ContentInsight, Platform, PublishLog

API_VERSION = "v21.0"
METRICS = "reach,likes,comments,shares,saved,views"
KNOWN_METRICS = ("reach", "likes", "comments", "shares", "saved", "views")


def _relay_url() -> str:
    return config(
        "PUBLISHER_IG_RELAY_URL", default="http://127.0.0.1:3297/ig"
    ).rstrip("/")


def _relay_headers() -> dict:
    return {"X-Relay-Token": config("PUBLISHER_IG_RELAY_TOKEN", default="")}


def fetch_media_insights(media_id: str, access_token: str) -> dict:
    """GET /v21.0/{media_id}/insights — خروجی: {نام متریک: مقدار}. در خطا RuntimeError."""
    resp = requests.get(
        f"{_relay_url()}/{API_VERSION}/{media_id}/insights",
        params={"metric": METRICS, "access_token": access_token},
        headers=_relay_headers(),
        timeout=15,
    )
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"پاسخ نامعتبر: {resp.text[:200]}")
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error") or {}
        raise RuntimeError(err.get("message") or f"HTTP {resp.status_code}")
    return {
        item.get("name"): (item.get("values") or [{}])[0].get("value", 0)
        for item in data.get("data", [])
    }


class Command(BaseCommand):
    help = "دریافت آمار پست‌های اینستاگرام از Graph API و ذخیره در ContentInsight"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="فقط چاپ آمار — هیچ رکوردی ذخیره نمی‌شود")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        platform = (
            Platform.objects.filter(slug="instagram")
            .select_related("credential").first()
        )
        if platform is None:
            raise CommandError("پلتفرم instagram تعریف نشده است")
        cred = getattr(platform, "credential", None)
        if cred is None or not cred.is_active:
            raise CommandError("اعتبارنامه اینستاگرام پیکربندی یا فعال نیست")
        access_token = (cred.credentials or {}).get("access_token", "")
        if not access_token:
            raise CommandError("access_token در اعتبارنامه اینستاگرام موجود نیست")

        logs = (
            PublishLog.objects
            .filter(platform=platform, status=PublishLog.Status.SUCCESS)
            .exclude(external_message_id="")
            .select_related("job__post")
        )
        self.stdout.write(f"{logs.count()} لاگ موفق اینستاگرام با شناسه مدیا پیدا شد")

        ok = failed = 0
        for log in logs:
            media_id = log.external_message_id
            try:
                metrics = fetch_media_insights(media_id, access_token)
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.WARNING(
                    f"لاگ {log.id} (مدیا {media_id}): دریافت آمار ناموفق — {exc}"
                ))
                continue
            mapped = {name: int(metrics.get(name) or 0) for name in KNOWN_METRICS}
            if dry_run:
                self.stdout.write(
                    f"(dry-run) «{log.job.post.title}» ← "
                    + "، ".join(f"{k}: {v}" for k, v in mapped.items())
                )
                continue
            ContentInsight.objects.update_or_create(
                log=log,
                defaults={"post": log.job.post, "raw": metrics, **mapped},
            )
            ok += 1
            self.stdout.write(
                f"«{log.job.post.title}» ← بازدید {mapped['views']}، ذخیره {mapped['saved']}، ریچ {mapped['reach']}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("(dry-run) هیچ رکوردی ذخیره نشد."))
        else:
            summary = f"{ok} آمار ذخیره/به‌روز شد"
            if failed:
                summary += f"، {failed} مورد با خطا مواجه شد"
            self.stdout.write(self.style.SUCCESS(summary))
