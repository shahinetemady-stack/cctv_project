"""
کامند generate_hook — ساخت کلیپ قلاب سینمایی AI (Veo 3.1) برای یک پست.

  python manage.py generate_hook --post-id 12

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

from apps.publisher.models import ChannelPost
from apps.publisher.video.aiclip import generate_hook_clip
from apps.publisher.video.builder import VideoBuildError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "ساخت کلیپ قلاب سینمایی AI (Veo) برای یک پست"

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
        post.save(update_fields=["hook_status", "hook_error"])

        out_dir = Path(settings.MEDIA_ROOT) / "publisher" / "hooks" / timezone.now().strftime("%Y/%m")
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=out_dir, suffix=".mp4", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            generate_hook_clip(post, tmp_path)
            name = f"hook-{post.pk}-{tmp_path.stem}.mp4"  # upload_to مسیر publisher/hooks/%Y/%m را می‌سازد
            with tmp_path.open("rb") as fh:
                post.hook_clip.save(name, File(fh), save=True)
            post.hook_status = ChannelPost.HookStatus.READY
            post.hook_ready_at = timezone.now()
            post.save(update_fields=["hook_status", "hook_ready_at"])
        except VideoBuildError as exc:
            post.hook_status = ChannelPost.HookStatus.FAILED
            post.hook_error = str(exc)[:500]
            post.save(update_fields=["hook_status", "hook_error"])
            self.stderr.write(self.style.ERROR(f"#{post.id} ساخت هوک ناموفق: {exc}"))
            return
        except Exception as exc:
            logger.exception(f"[generate_hook] خطای غیرمنتظره برای پست #{post.id}")
            post.hook_status = ChannelPost.HookStatus.FAILED
            post.hook_error = f"خطای غیرمنتظره: {exc}"[:500]
            post.save(update_fields=["hook_status", "hook_error"])
            self.stderr.write(self.style.ERROR(f"#{post.id} خطای غیرمنتظره: {exc}"))
            return
        finally:
            tmp_path.unlink(missing_ok=True)

        self.stdout.write(self.style.SUCCESS(f"#{post.id} هوک AI ساخته و ضمیمه شد"))
