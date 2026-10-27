"""
کامند generate_hook — ساخت کلیپ قلاب سینمایی AI برای یک پست.

  python manage.py generate_hook --post-id 12

زنجیرهٔ موتورها بر اساس video_provider_priority تنظیمات استودیو (پیش‌فرض
veo,hf): هر موتور به ترتیب امتحان می‌شود؛ خطاهای سهمیه (QuotaExceeded / 429)
موتور بعدی را فعال می‌کنند و بقیهٔ خطاها بلافاصله fail می‌شوند. موتور موفق در
hook_provider پست ثبت می‌شود.

معمولاً از API (POST /api/publisher/posts/<pk>/generate-hook/) به‌صورت
ساب‌پروسس جداگانه اجرا می‌شود. وضعیت روی خود پست (hook_status/hook_error)
به‌روز می‌شود تا رابط کاربری با polling نتیجه را ببیند.
"""

import logging
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.publisher.models import ChannelPost, PublisherSettings
from apps.publisher.video.aiclip import generate_hook_clip
from apps.publisher.video.builder import VideoBuildError
from apps.publisher.video.hfclip import QuotaExceeded, _is_quota, generate_hook_clip_hf

logger = logging.getLogger(__name__)

PROVIDERS = {
    "veo": generate_hook_clip,
    "hf": generate_hook_clip_hf,
}


class Command(BaseCommand):
    help = "ساخت کلیپ قلاب سینمایی AI (Veo یا HF) برای یک پست"

    def add_arguments(self, parser):
        parser.add_argument("--post-id", type=int, required=True, help="شناسهٔ پست")

    def handle(self, *args, **options):
        post = (
            ChannelPost.objects
            .filter(pk=options["post_id"])
            .select_related("idea", "idea__product")
            .first()
        )
        if post is None:
            self.stderr.write(self.style.ERROR(f"پست {options['post_id']} یافت نشد"))
            return

        post.hook_status = ChannelPost.HookStatus.BUILDING
        post.hook_error = ""
        post.hook_provider = ""
        post.save(update_fields=["hook_status", "hook_error", "hook_provider"])

        out_dir = Path(settings.MEDIA_ROOT) / "publisher" / "hooks" / timezone.now().strftime("%Y/%m")
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=out_dir, suffix=".mp4", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            provider = self._run_chain(post, tmp_path)
            if provider is None:
                return  # خطاها در hook_error ثبت شده‌اند
            name = f"hook-{post.pk}-{tmp_path.stem}.mp4"  # upload_to مسیر publisher/hooks/%Y/%m را می‌سازد
            with tmp_path.open("rb") as fh:
                post.hook_clip.save(name, File(fh), save=True)
            post.hook_status = ChannelPost.HookStatus.READY
            post.hook_provider = provider
            post.hook_ready_at = timezone.now()
            post.save(update_fields=["hook_status", "hook_provider", "hook_ready_at"])
        finally:
            tmp_path.unlink(missing_ok=True)

        self.stdout.write(self.style.SUCCESS(f"#{post.id} هوک AI با موتور {provider} ساخته و ضمیمه شد"))

    def _provider_order(self) -> list[str]:
        priority = PublisherSettings.get_instance().video_provider_priority
        order = [p.strip() for p in priority.split(",") if p.strip() in PROVIDERS]
        return order or ["veo"]

    def _fail(self, post, message: str):
        post.hook_status = ChannelPost.HookStatus.FAILED
        post.hook_error = message[:500]
        post.save(update_fields=["hook_status", "hook_error"])
        self.stderr.write(self.style.ERROR(f"#{post.id} ساخت هوک ناموفق: {message}"))

    def _run_chain(self, post, tmp_path) -> str | None:
        """موتورها را به ترتیب اولویت امتحان می‌کند؛ نام موتور موفق یا None."""
        errors = []
        for name in self._provider_order():
            try:
                PROVIDERS[name](post, tmp_path)
                return name
            except QuotaExceeded as exc:
                logger.warning(f"[generate_hook] موتور {name} سهمیه‌اش تمام شده: {exc}")
                errors.append(f"{name}: {exc}")
            except VideoBuildError as exc:
                if _is_quota(str(exc)):
                    logger.warning(f"[generate_hook] موتور {name} خطای سهمیه: {exc}")
                    errors.append(f"{name}: {exc}")
                    continue
                self._fail(post, str(exc))
                return None
            except Exception as exc:
                logger.exception(f"[generate_hook] خطای غیرمنتظره موتور {name} برای پست #{post.id}")
                self._fail(post, f"خطای غیرمنتظره: {exc}")
                return None
        self._fail(post, " | ".join(errors) or "هیچ موتوری پیکربندی نشده است")
        return None
