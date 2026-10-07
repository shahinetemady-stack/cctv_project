"""
کامند build_content_media — ساخت ویدیوی خودکار برای پست‌های پیش‌نویس.

  python manage.py build_content_media --post-id 12
  python manage.py build_content_media --all
  python manage.py build_content_media --all --dry-run
"""

import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.publisher.models import ChannelPost
from apps.publisher.video.builder import VideoBuildError, build_video_for_post

VIDEO_TYPES = [
    ChannelPost.ContentType.POST,
    ChannelPost.ContentType.STORY,
    ChannelPost.ContentType.REEL,
]


class Command(BaseCommand):
    help = "ساخت ویدیوی ریل/استوری/پست از تصاویر محصول برای پست‌های پیش‌نویس بدون ویدیو"

    def add_arguments(self, parser):
        parser.add_argument("--post-id", type=int, help="شناسهٔ یک پست مشخص")
        parser.add_argument("--all", action="store_true",
                            help="همهٔ پیش‌نویس‌های reel/story/post بدون ویدیو")
        parser.add_argument("--dry-run", action="store_true",
                            help="فقط فهرست نامزدها را نمایش بده، چیزی نساز")

    def handle(self, *args, **options):
        post_id = options["post_id"]
        if not post_id and not options["all"]:
            self.stderr.write(self.style.ERROR("یکی از --post-id یا --all لازم است"))
            return

        if post_id:
            posts = list(ChannelPost.objects.filter(pk=post_id))
            if not posts:
                self.stderr.write(self.style.ERROR(f"پست {post_id} یافت نشد"))
                return
        else:
            posts = list(
                ChannelPost.objects.filter(
                    approval_status=ChannelPost.ApprovalStatus.DRAFT,
                    content_type__in=VIDEO_TYPES,
                    video="",
                ).select_related("idea", "idea__product", "music_track")
            )

        if options["dry_run"]:
            self.stdout.write(f"{len(posts)} نامزد ساخت ویدیو:")
            for p in posts:
                self.stdout.write(
                    f"  #{p.id} [{p.content_type}] {p.title}"
                    f"{' (ویدیو دارد!)' if p.video else ''}"
                )
            return

        ok = failed = skipped = 0
        for post in posts:
            if post.video:
                skipped += 1
                self.stdout.write(f"#{post.id} رد شد — از قبل ویدیو دارد")
                continue
            try:
                self._build_and_attach(post)
            except VideoBuildError as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"#{post.id} ناموفق: {exc}"))
            except Exception as exc:  # خطای غیرمنتظره یک پست، بچ را متوقف نمی‌کند
                failed += 1
                self.stderr.write(self.style.ERROR(f"#{post.id} خطای غیرمنتظره: {exc}"))
            else:
                ok += 1
                self.stdout.write(self.style.SUCCESS(f"#{post.id} ویدیو ساخته و ضمیمه شد"))

        self.stdout.write(f"نتیجه: {ok} موفق، {failed} ناموفق، {skipped} ردشده")

    def _build_and_attach(self, post):
        out_dir = Path(settings.MEDIA_ROOT) / "publisher" / timezone.now().strftime("%Y/%m")
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=out_dir, suffix=".mp4", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            build_video_for_post(post, tmp_path)
            name = f"post-{post.pk}-{tmp_path.stem}.mp4"  # upload_to خودش مسیر publisher/%Y/%m را می‌سازد
            with tmp_path.open("rb") as fh:
                post.video.save(name, File(fh), save=True)
        finally:
            tmp_path.unlink(missing_ok=True)
