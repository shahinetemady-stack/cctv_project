"""
apps/publisher/views.py
────────────────────────
APIهای انتشار محتوا در پیام‌رسان‌ها — همه APIView ساده با دسترسی RBAC.

GET  /api/publisher/platforms/           لیست پلتفرم‌ها (publisher_view)
GET  /api/publisher/credentials/         اعتبارنامه‌ها با مقادیر ماسک‌شده (publisher_credentials)
POST /api/publisher/credentials/save/    ذخیره/ویرایش اعتبارنامه (publisher_credentials)
GET/POST /api/publisher/posts/           لیست/ساخت پست (multipart)
GET/POST /api/publisher/ideas/           لیست ایده‌ها / ثبت ایدهٔ دستی + تولید کپشن با LLM
POST /api/publisher/posts/<pk>/approve/  تأیید پیش‌نویس (+ انتشار/زمان‌بندی اختیاری)
POST /api/publisher/posts/<pk>/reject/   رد پیش‌نویس (publisher_approve)
POST /api/publisher/posts/<pk>/build-media/  ساخت/بازسازی ویدیوی پست با FFmpeg (publisher_publish)
POST /api/publisher/posts/<pk>/generate-hook/  ساخت کلیپ قلاب AI با Veo در بک‌گراند (publisher_publish)
POST /api/publisher/publish/             ساخت کار انتشار (publisher_publish)
GET  /api/publisher/jobs/                لیست کارهای انتشار
GET  /api/publisher/jobs/<pk>/           جزئیات کار + لاگ‌ها
POST /api/publisher/logs/<pk>/retry/     تلاش مجدد یک لاگ ناموفق
GET/POST /api/publisher/music/           کتابخانهٔ موزیک (لیست/آپلود — publisher_publish)
GET  /api/publisher/insights/            گزارش عملکرد پست‌های اینستاگرام (publisher_view)
"""

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.views import _has_staff_perm

from .contentgen import CONTENT_CATEGORIES, generate_caption
from .crypto import encrypt_json
from .models import ChannelCredential, ChannelPost, ContentIdea, ContentInsight, MusicTrack, Platform, PublishJob, PublishLog

def _forbidden():
    return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a"}
IMAGE_MAX_BYTES = 10 * 1024 * 1024   # ۱۰ مگابایت
VIDEO_MAX_BYTES = 50 * 1024 * 1024   # ۵۰ مگابایت
AUDIO_MAX_BYTES = 20 * 1024 * 1024   # ۲۰ مگابایت


def _media_url(request, field):
    if not field:
        return None
    return request.build_absolute_uri(field.url)


def _post_payload(request, post):
    return {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "content_type": post.content_type,
        "approval_status": post.approval_status,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "hashtags": post.hashtags,
        "idea_id": post.idea_id,
        "image_url": _media_url(request, post.image),
        "video_url": _media_url(request, post.video),
        "hook_status": post.hook_status,
        "hook_clip_url": _media_url(request, post.hook_clip),
        "hook_error": post.hook_error,
        "link": post.link,
        "created_by": post.created_by.get_full_name() if post.created_by else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


def _parse_scheduled_at(value):
    """رشتهٔ ISO8601 → datetime آگاه از منطقهٔ زمانی؛ مقدار نامعتبر ValueError."""
    dt = parse_datetime(str(value))
    if dt is None:
        raise ValueError("فرمت scheduled_at نامعتبر است — ISO8601 بفرستید")
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _create_publish_job(post, platform_ids, user, scheduled_at=None):
    """ساخت PublishJob + یک PublishLog به ازای هر پلتفرم — منطق مشترک publish و approve.
    پلتفرم غیرفعال رد می‌شود؛ پلتفرم بدون اعتبارنامه فعال، لاگ failed می‌گیرد.
    در خطا Response برمی‌گرداند، در غیر این صورت (job, skipped)."""
    if not isinstance(platform_ids, list) or not platform_ids:
        return Response({"error": "حداقل یک پلتفرم انتخاب کنید"}, status=400)
    platforms = list(Platform.objects.filter(pk__in=platform_ids).select_related("credential"))
    if not platforms:
        return Response({"error": "هیچ‌کدام از پلتفرم‌های انتخاب‌شده یافت نشد"}, status=400)

    with transaction.atomic():
        job = PublishJob.objects.create(post=post, created_by=user)
        skipped = []
        for p in platforms:
            if not p.is_active:
                skipped.append(p.name)
                continue
            cred = getattr(p, "credential", None)
            if cred is None or not cred.is_active:
                PublishLog.objects.create(
                    job=job, platform=p, status=PublishLog.Status.FAILED,
                    error_message="اعتبارنامه پیکربندی نشده",
                )
            else:
                PublishLog.objects.create(job=job, platform=p, next_attempt_at=scheduled_at)
    return job, skipped


def _validate_upload(request):
    """تصویر/ویدیو ارسالی را بررسی می‌کند؛ در خطا Response، در غیر این صورت None."""
    image = request.FILES.get("image")
    if image is not None:
        ext = (image.name.rsplit(".", 1)[-1] if "." in image.name else "").lower()
        if ext not in IMAGE_EXTENSIONS:
            return Response({"error": "فرمت تصویر مجاز نیست — فقط jpg، jpeg، png یا webp"}, status=400)
        if image.size > IMAGE_MAX_BYTES:
            return Response({"error": "حجم تصویر نباید بیشتر از ۱۰ مگابایت باشد"}, status=400)
    video = request.FILES.get("video")
    if video is not None:
        ext = (video.name.rsplit(".", 1)[-1] if "." in video.name else "").lower()
        if ext not in VIDEO_EXTENSIONS:
            return Response({"error": "فرمت ویدیو مجاز نیست — فقط mp4 یا mov"}, status=400)
        if video.size > VIDEO_MAX_BYTES:
            return Response({"error": "حجم ویدیو نباید بیشتر از ۵۰ مگابایت باشد"}, status=400)
    return None


class PlatformListView(APIView):
    """GET /api/publisher/platforms/ — پلتفرم‌ها + وضعیت پیکربندی اعتبارنامه."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_staff_perm(request.user, "publisher_view"):
            return _forbidden()
        platforms = Platform.objects.all().select_related("credential")
        return Response([{
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "is_active": p.is_active,
            "configured": bool(
                getattr(p, "credential", None)
                and p.credential.is_active
                and p.credential.chat_id
            ),
        } for p in platforms])


class CredentialListView(APIView):
    """
    GET /api/publisher/credentials/ — اعتبارنامه‌ها با مقادیر ماسک‌شده.
    فقط کلیدهای دیکشنری اعتبارنامه و chat_id نمایش داده می‌شود؛ هرگز مقادیر.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_staff_perm(request.user, "publisher_credentials"):
            return _forbidden()
        platforms = Platform.objects.all().select_related("credential")
        result = []
        for p in platforms:
            cred = getattr(p, "credential", None)
            row = {
                "platform_id": p.id,
                "platform_slug": p.slug,
                "platform_name": p.name,
                "credential_id": cred.id if cred else None,
                "chat_id": cred.chat_id if cred else "",
                "is_active": cred.is_active if cred else False,
                "credential_keys": [],
                "updated_at": cred.updated_at.isoformat() if cred else None,
            }
            if cred:
                try:
                    row["credential_keys"] = sorted(cred.credentials.keys())
                except Exception:
                    row["credential_keys"] = ["<غیرقابل رمزگشایی>"]
            result.append(row)
        return Response(result)


class CredentialSaveView(APIView):
    """
    POST /api/publisher/credentials/save/
    بدنه: {platform: <id>, credentials: {...}, chat_id: "...", is_active: bool}
    اعتبارنامه را upsert می‌کند — JSON با Fernet رمزنگاری می‌شود.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _has_staff_perm(request.user, "publisher_credentials"):
            return _forbidden()
        platform = Platform.objects.filter(pk=request.data.get("platform")).first()
        if platform is None:
            return Response({"error": "پلتفرم یافت نشد"}, status=404)
        credentials = request.data.get("credentials")
        if not isinstance(credentials, dict) or not credentials:
            return Response({"error": "اعتبارنامه باید یک آبجکت JSON غیرخالی باشد"}, status=400)
        chat_id = str(request.data.get("chat_id") or "").strip()
        is_active = bool(request.data.get("is_active", True))

        with transaction.atomic():
            cred, created = ChannelCredential.objects.get_or_create(
                platform=platform,
                defaults={
                    "credentials_encrypted": encrypt_json(credentials),
                    "chat_id": chat_id,
                    "is_active": is_active,
                },
            )
            if not created:
                cred.credentials_encrypted = encrypt_json(credentials)
                cred.chat_id = chat_id
                cred.is_active = is_active
                cred.save(update_fields=[
                    "credentials_encrypted", "chat_id", "is_active", "updated_at",
                ])
        return Response({"success": True, "credential_id": cred.id})


class PostListCreateView(APIView):
    """
    GET  /api/publisher/posts/  — پست‌های اخیر (publisher_view)
        فیلتر: ?status=draft|approved|rejected و ?content_type=post|story|reel
    POST /api/publisher/posts/  — ساخت پست با multipart (publisher_publish)
    فیلدها: title, body, link?, image?, video?
    پست‌های ساخته‌شده از این مسیر (کامپوز دستی) مستقیم approved می‌شوند تا
    جریان قبلی compose→publish بدون تغییر کار کند.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_staff_perm(request.user, "publisher_view"):
            return _forbidden()
        posts = ChannelPost.objects.select_related("created_by")
        status = request.query_params.get("status")
        if status in ChannelPost.ApprovalStatus.values:
            posts = posts.filter(approval_status=status)
        content_type = request.query_params.get("content_type")
        if content_type in ChannelPost.ContentType.values:
            posts = posts.filter(content_type=content_type)
        return Response([_post_payload(request, p) for p in posts[:50]])

    def post(self, request):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        title = (request.data.get("title") or "").strip()
        body = (request.data.get("body") or "").strip()
        if not title:
            return Response({"error": "عنوان پست الزامی است"}, status=400)
        if not body:
            return Response({"error": "متن محتوا الزامی است"}, status=400)
        invalid = _validate_upload(request)
        if invalid is not None:
            return invalid

        with transaction.atomic():
            post = ChannelPost.objects.create(
                title=title,
                body=body,
                link=(request.data.get("link") or "").strip(),
                image=request.FILES.get("image"),
                video=request.FILES.get("video"),
                created_by=request.user,
                approval_status=ChannelPost.ApprovalStatus.APPROVED,
            )
        return Response(_post_payload(request, post), status=201)


class IdeaListCreateView(APIView):
    """
    GET  /api/publisher/ideas/  — ایده‌های اخیر (publisher_view)
    POST /api/publisher/ideas/  — ثبت ایدهٔ دستی (publisher_publish)
        بدنه: {title, description?, category?, product_id?, content_type?}
        کپشن و هشتگ با LLM تولید و یک پیش‌نویس پست (draft) به ایده لینک می‌شود.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_staff_perm(request.user, "publisher_view"):
            return _forbidden()
        ideas = ContentIdea.objects.prefetch_related("posts")[:50]
        return Response([{
            "id": i.id,
            "title": i.title,
            "category": i.category,
            "source": i.source,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "post_id": (i.posts.all()[0].id if i.posts.all() else None),
        } for i in ideas])

    def post(self, request):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        title = (request.data.get("title") or "").strip()
        if not title:
            return Response({"error": "عنوان ایده الزامی است"}, status=400)
        description = (request.data.get("description") or "").strip()
        category = request.data.get("category") or ContentIdea.Category.PRODUCT_SHOWCASE
        if category not in CONTENT_CATEGORIES:
            category = ContentIdea.Category.PRODUCT_SHOWCASE
        content_type = request.data.get("content_type") or ChannelPost.ContentType.POST
        if content_type not in ChannelPost.ContentType.values:
            content_type = ChannelPost.ContentType.POST
        product = None
        product_id = request.data.get("product_id")
        if product_id:
            from apps.catalog.models import Product
            product = Product.objects.filter(pk=product_id, is_active=True).first()
            if product is None:
                return Response({"error": "محصول یافت نشد"}, status=404)

        try:
            generated = generate_caption(title, description, category, product)
        except Exception as exc:
            return Response({"error": f"تولید کپشن با هوش مصنوعی ناموفق بود: {exc}"}, status=502)

        with transaction.atomic():
            idea = ContentIdea.objects.create(
                title=title,
                description=description,
                source=ContentIdea.Source.MANUAL,
                category=category,
                product=product,
                status=ContentIdea.Status.USED,
            )
            post = ChannelPost.objects.create(
                title=title,
                body=generated["caption"] or title,
                content_type=content_type,
                approval_status=ChannelPost.ApprovalStatus.DRAFT,
                idea=idea,
                hashtags=" ".join(f"#{h}" for h in generated["hashtags"]),
                created_by=request.user,
            )
        return Response({
            "idea_id": idea.id,
            "post_id": post.id,
            "caption": generated["caption"],
            "hashtags": generated["hashtags"],
        }, status=201)


class PostApproveView(APIView):
    """
    POST /api/publisher/posts/<pk>/approve/  (publisher_approve)
    پیش‌نویس را تأیید می‌کند. بدنهٔ اختیاری: {platform_ids: [...], scheduled_at: "ISO8601"}
    — با platform_ids بلافاصله کار انتشار (با زمان‌بندی در صورت وجود) ساخته می‌شود.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "publisher_approve"):
            return _forbidden()
        post = ChannelPost.objects.filter(pk=pk).first()
        if post is None:
            return Response({"error": "پست یافت نشد"}, status=404)

        scheduled_at = None
        if request.data.get("scheduled_at"):
            try:
                scheduled_at = _parse_scheduled_at(request.data["scheduled_at"])
            except ValueError as exc:
                return Response({"error": str(exc)}, status=400)
            post.scheduled_at = scheduled_at

        post.approval_status = ChannelPost.ApprovalStatus.APPROVED
        post.save(update_fields=["approval_status", "scheduled_at"])

        result = {"success": True, "post_id": post.id, "approval_status": post.approval_status}
        if request.data.get("platform_ids"):
            job_result = _create_publish_job(post, request.data["platform_ids"], request.user, scheduled_at)
            if isinstance(job_result, Response):
                return job_result
            job, skipped = job_result
            result.update({"job_id": job.id, "skipped_platforms": skipped})
        return Response(result)


class PostRejectView(APIView):
    """POST /api/publisher/posts/<pk>/reject/  (publisher_approve) — رد پیش‌نویس."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "publisher_approve"):
            return _forbidden()
        post = ChannelPost.objects.filter(pk=pk).first()
        if post is None:
            return Response({"error": "پست یافت نشد"}, status=404)
        post.approval_status = ChannelPost.ApprovalStatus.REJECTED
        post.save(update_fields=["approval_status"])
        return Response({"success": True, "post_id": post.id, "approval_status": post.approval_status})


class PostBuildMediaView(APIView):
    """
    POST /api/publisher/posts/<pk>/build-media/  (publisher_publish)
    ویدیوی پست را از تصاویر محصول با FFmpeg می‌سازد و به فیلد video ضمیمه می‌کند.
    اگر پست ویدیو دارد 409 برمی‌گردد مگر با ?force=1 که بازسازی انجام شود.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        post = ChannelPost.objects.filter(pk=pk).first()
        if post is None:
            return Response({"error": "پست یافت نشد"}, status=404)
        if post.video and request.query_params.get("force") != "1":
            return Response(
                {"error": "این پست از قبل ویدیو دارد — برای بازسازی ?force=1 بفرستید"},
                status=409,
            )

        import tempfile
        from pathlib import Path

        from django.conf import settings
        from django.core.files import File

        from .video.builder import VideoBuildError, build_video_for_post

        out_dir = Path(settings.MEDIA_ROOT) / "publisher" / timezone.now().strftime("%Y/%m")
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=out_dir, suffix=".mp4", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            build_video_for_post(post, tmp_path)
            with tmp_path.open("rb") as fh:
                old_video = post.video.name if post.video else None
                post.video.save(f"post-{post.pk}-{tmp_path.stem}.mp4", File(fh), save=True)
            if old_video:
                post.video.storage.delete(old_video)
        except VideoBuildError as exc:
            return Response({"error": str(exc)}, status=502)
        finally:
            tmp_path.unlink(missing_ok=True)
        return Response(_post_payload(request, post))


class PostGenerateHookView(APIView):
    """
    POST /api/publisher/posts/<pk>/generate-hook/  (publisher_publish)
    ساخت کلیپ قلاب سینمایی ۸ ثانیه‌ای با Google Veo 3.1 در بک‌گراند
    (ساب‌پروسس manage.py generate_hook — مثل الگوی اجرای اسکرپرها در leads).

    هزینه: هر هوک موفق حدود ۱ دلار (۸ ثانیه veo-3.1-fast-generate-preview) —
    برای کنترل هزینه، روزانه حداکثر ۵ هوک موفق مجاز است.
    """
    permission_classes = [IsAuthenticated]

    DAILY_LIMIT = 5

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        post = ChannelPost.objects.filter(pk=pk).first()
        if post is None:
            return Response({"error": "پست یافت نشد"}, status=404)
        if post.hook_status == ChannelPost.HookStatus.BUILDING:
            return Response({"error": "ساخت هوک این پست در حال انجام است"}, status=409)
        if post.hook_status == ChannelPost.HookStatus.READY:
            return Response({"error": "این پست از قبل هوک AI دارد"}, status=409)

        today_count = ChannelPost.objects.filter(
            hook_status=ChannelPost.HookStatus.READY,
            hook_ready_at__date=timezone.localdate(),
        ).count()
        if today_count >= self.DAILY_LIMIT:
            return Response(
                {"error": f"سقف روزانهٔ {self.DAILY_LIMIT} هوک AI پر شده است — فردا دوباره تلاش کنید"},
                status=429,
            )

        post.hook_status = ChannelPost.HookStatus.BUILDING
        post.hook_error = ""
        post.save(update_fields=["hook_status", "hook_error"])

        import subprocess
        import sys

        from django.conf import settings

        log = open("/tmp/generate_hook_panel.log", "ab")
        subprocess.Popen(
            [sys.executable, "-u", "manage.py", "generate_hook", "--post-id", str(post.pk)],
            cwd=settings.BASE_DIR, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return Response({"hook_status": post.hook_status}, status=202)


class PublishCreateView(APIView):
    """
    POST /api/publisher/publish/
    بدنه: {post_id: <id>, platform_ids: [<id>, ...], scheduled_at?: "ISO8601"}
    یک PublishJob + یک PublishLog به ازای هر پلتفرم فعال می‌سازد.
    پست ردشده (rejected) قابل انتشار نیست؛ پیش‌نویس و تأییدشده آزادند تا
    پست‌های قدیمی (قبل از قابلیت تأیید) بدون مانع منتشر شوند.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        post = ChannelPost.objects.filter(pk=request.data.get("post_id")).first()
        if post is None:
            return Response({"error": "پست یافت نشد"}, status=404)
        if post.approval_status == ChannelPost.ApprovalStatus.REJECTED:
            return Response({"error": "پست رد شده و قابل انتشار نیست"}, status=400)

        scheduled_at = None
        if request.data.get("scheduled_at"):
            try:
                scheduled_at = _parse_scheduled_at(request.data["scheduled_at"])
            except ValueError as exc:
                return Response({"error": str(exc)}, status=400)
            post.scheduled_at = scheduled_at
            post.save(update_fields=["scheduled_at"])

        job_result = _create_publish_job(post, request.data.get("platform_ids"), request.user, scheduled_at)
        if isinstance(job_result, Response):
            return job_result
        job, skipped = job_result
        return Response({"job_id": job.id, "skipped_platforms": skipped}, status=201)


class JobListView(APIView):
    """GET /api/publisher/jobs/ — ۳۰ کار اخیر با خلاصه وضعیت هر پلتفرم."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_staff_perm(request.user, "publisher_view"):
            return _forbidden()
        jobs = (
            PublishJob.objects
            .select_related("post", "created_by")
            .prefetch_related("logs__platform")[:30]
        )
        return Response([{
            "id": j.id,
            "status": j.status,
            "post_title": j.post.title,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "platforms": [{
                "slug": log.platform.slug,
                "name": log.platform.name,
                "status": log.status,
            } for log in j.logs.all()],
        } for j in jobs])


class JobDetailView(APIView):
    """GET /api/publisher/jobs/<pk>/ — جزئیات کار + لاگ هر پلتفرم."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _has_staff_perm(request.user, "publisher_view"):
            return _forbidden()
        job = (
            PublishJob.objects
            .select_related("post")
            .prefetch_related("logs__platform")
            .filter(pk=pk).first()
        )
        if job is None:
            return Response({"error": "کار انتشار یافت نشد"}, status=404)
        return Response({
            "id": job.id,
            "status": job.status,
            "post": {
                "id": job.post.id,
                "title": job.post.title,
                "body": job.post.body,
                "image_url": _media_url(request, job.post.image),
                "video_url": _media_url(request, job.post.video),
                "link": job.post.link,
            },
            "logs": [{
                "id": log.id,
                "platform_slug": log.platform.slug,
                "platform_name": log.platform.name,
                "status": log.status,
                "error_message": log.error_message,
                "attempt_count": log.attempt_count,
                "external_message_id": log.external_message_id,
                "updated_at": log.updated_at.isoformat() if log.updated_at else None,
            } for log in job.logs.all()],
        })


class LogRetryView(APIView):
    """
    POST /api/publisher/logs/<pk>/retry/
    لاگ ناموفق را به حالت در انتظار برمی‌گرداند تا کران دوباره تلاش کند.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        log = PublishLog.objects.select_related("job").filter(pk=pk).first()
        if log is None:
            return Response({"error": "لاگ یافت نشد"}, status=404)
        if log.status != PublishLog.Status.FAILED:
            return Response({"error": "فقط لاگ ناموفق قابل تلاش مجدد است"}, status=400)

        with transaction.atomic():
            log.status = PublishLog.Status.PENDING
            log.attempt_count = 0
            log.next_attempt_at = None
            log.error_message = ""
            log.save(update_fields=[
                "status", "attempt_count", "next_attempt_at", "error_message", "updated_at",
            ])
            job = log.job
            job.status = PublishJob.Status.PENDING
            job.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "log_id": log.id, "job_id": job.id})


def _music_payload(request, track):
    return {
        "id": track.id,
        "title": track.title,
        "mood": track.mood,
        "file_url": _media_url(request, track.file),
        "is_active": track.is_active,
    }


class MusicTrackListCreateView(APIView):
    """
    GET  /api/publisher/music/  — فهرست موزیک‌های کتابخانه (publisher_publish)
    POST /api/publisher/music/  — آپلود موزیک با multipart (publisher_publish)
    فیلدها: title، mood?، file — فرمت مجاز mp3/wav/m4a تا ۲۰ مگابایت.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        tracks = MusicTrack.objects.all()[:100]
        return Response([_music_payload(request, t) for t in tracks])

    def post(self, request):
        if not _has_staff_perm(request.user, "publisher_publish"):
            return _forbidden()
        title = (request.data.get("title") or "").strip()
        if not title:
            return Response({"error": "عنوان موزیک الزامی است"}, status=400)
        file = request.FILES.get("file")
        if file is None:
            return Response({"error": "فایل موزیک الزامی است"}, status=400)
        ext = (file.name.rsplit(".", 1)[-1] if "." in file.name else "").lower()
        if ext not in AUDIO_EXTENSIONS:
            return Response({"error": "فرمت موزیک مجاز نیست — فقط mp3، wav یا m4a"}, status=400)
        if file.size > AUDIO_MAX_BYTES:
            return Response({"error": "حجم موزیک نباید بیشتر از ۲۰ مگابایت باشد"}, status=400)

        track = MusicTrack.objects.create(
            title=title,
            mood=(request.data.get("mood") or "").strip(),
            file=file,
        )
        return Response(_music_payload(request, track), status=201)


class InsightListView(APIView):
    """
    GET /api/publisher/insights/ — گزارش عملکرد پست‌های اینستاگرام (publisher_view)
    خلاصهٔ هر پست با متریک‌های اینسایت، مرتب‌شده بر اساس ریچ نزولی.
    داده توسط کامند fetch_ig_insights پر می‌شود.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_staff_perm(request.user, "publisher_view"):
            return _forbidden()
        insights = (
            ContentInsight.objects
            .select_related("post", "log")
            .order_by("-reach", "-views")[:50]
        )
        return Response([{
            "post_id": ins.post_id,
            "title": ins.post.title,
            "content_type": ins.post.content_type,
            "thumbnail": _media_url(request, ins.post.image) or _media_url(request, ins.post.video),
            "published_at": ins.log.updated_at.isoformat() if ins.log.updated_at else None,
            "reach": ins.reach,
            "likes": ins.likes,
            "comments": ins.comments,
            "shares": ins.shares,
            "saved": ins.saved,
            "views": ins.views,
            "fetched_at": ins.fetched_at.isoformat() if ins.fetched_at else None,
        } for ins in insights])
