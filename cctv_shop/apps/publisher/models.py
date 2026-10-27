"""
apps/publisher/models.py
─────────────────────────
انتشار محتوا در پیام‌رسان‌ها (تلگرام، بله، ایتا، روبیکا، واتساپ).

Platform          → پیام‌رسان‌های پشتیبانی‌شده
ChannelCredential → اعتبارنامه رمزنگاری‌شده هر پلتفرم (Fernet + SECRET_KEY)
ContentIdea       → ایدهٔ محتوا (خودکار/دستی) — منشأ پیش‌نویس پست‌ها
MusicTrack        → کتابخانهٔ موزیک برای ریل/استوری
ChannelPost       → محتوای آماده انتشار (مستقل از محتوای سایت)
PublishJob        → یک دستور انتشار روی چند پلتفرم
PublishLog        → وضعیت ارسال هر پلتفرم با قابلیت retry نمایی
ContentInsight    → آمار عملکرد پست‌های اینستاگرام (کامند fetch_ig_insights)
"""

from django.conf import settings
from django.db import models

from .crypto import decrypt_json


class Platform(models.Model):
    """پیام‌رسان پشتیبانی‌شده (تلگرام/بله/ایتا/روبیکا/واتساپ)."""

    name = models.CharField(max_length=100, verbose_name="نام")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="شناسه انگلیسی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        db_table = "publisher_platform"
        verbose_name = "پلتفرم"
        verbose_name_plural = "پلتفرم‌ها"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class ChannelCredential(models.Model):
    """اعتبارنامه اتصال به یک پلتفرم — JSON رمزنگاری‌شده با Fernet."""

    platform = models.OneToOneField(
        Platform, on_delete=models.CASCADE, related_name="credential",
        verbose_name="پلتفرم",
    )
    credentials_encrypted = models.TextField(verbose_name="اعتبارنامه رمزنگاری‌شده")
    chat_id = models.CharField(
        max_length=255, blank=True, verbose_name="شناسه کانال/چت مقصد",
        help_text="مثال: @channelusername یا شناسه عددی چت",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        db_table = "publisher_credential"
        verbose_name = "اعتبارنامه کانال"
        verbose_name_plural = "اعتبارنامه‌های کانال"

    def __str__(self):
        return f"اعتبارنامه {self.platform.name}"

    @property
    def credentials(self) -> dict:
        """اعتبارنامه رمزگشایی‌شده (دیکشنری)."""
        return decrypt_json(self.credentials_encrypted)


class ContentIdea(models.Model):
    """ایدهٔ محتوا — خودکار (کامند generate_content_ideas) یا دستی (API)؛ منشأ پیش‌نویس پست‌ها."""

    class Source(models.TextChoices):
        AUTO = "auto", "خودکار"
        MANUAL = "manual", "دستی"

    class Category(models.TextChoices):
        PRODUCT_SHOWCASE = "product_showcase", "معرفی محصول"
        EDUCATIONAL = "educational", "آموزشی"
        OFFER = "offer", "پیشنهاد/تخفیف"
        TREND = "trend", "ترند"
        BEHIND_SCENES = "behind_scenes", "پشت صحنه"

    class Status(models.TextChoices):
        NEW = "new", "جدید"
        USED = "used", "استفاده شده"
        REJECTED = "rejected", "رد شده"

    title = models.CharField(max_length=255, verbose_name="عنوان")
    description = models.TextField(blank=True, verbose_name="توضیح")
    source = models.CharField(
        max_length=20, choices=Source.choices,
        default=Source.AUTO, verbose_name="منشأ",
    )
    category = models.CharField(
        max_length=30, choices=Category.choices,
        default=Category.PRODUCT_SHOWCASE, verbose_name="دسته",
    )
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="content_ideas",
        verbose_name="محصول",
    )
    article = models.ForeignKey(
        "education.Article", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="content_ideas",
        verbose_name="مقاله",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.NEW, verbose_name="وضعیت",
    )
    signal = models.CharField(
        max_length=255, blank=True, verbose_name="منبع/سیگنال ایده",
        help_text="کدام سیگنال (ترند گوگل، سؤال مشتری، اینسایت) الهام‌بخش این ایده بود",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        db_table = "publisher_content_idea"
        verbose_name = "ایدهٔ محتوا"
        verbose_name_plural = "ایده‌های محتوا"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MusicTrack(models.Model):
    """کتابخانهٔ موزیک برای ریل/استوری."""

    title = models.CharField(max_length=255, verbose_name="عنوان")
    file = models.FileField(upload_to="music_library/", verbose_name="فایل")
    mood = models.CharField(max_length=50, blank=True, verbose_name="حال‌وهوا",
        help_text="مثال: energetic / calm / corporate")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        db_table = "publisher_music_track"
        verbose_name = "موزیک"
        verbose_name_plural = "کتابخانهٔ موزیک"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ChannelPost(models.Model):
    """محتوای آماده انتشار در پیام‌رسان‌ها — مستقل از محتوای سایت."""

    class ContentType(models.TextChoices):
        POST = "post", "پست"
        STORY = "story", "استوری"
        REEL = "reel", "ریل"

    class ApprovalStatus(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        APPROVED = "approved", "تأیید شده"
        REJECTED = "rejected", "رد شده"

    class HookStatus(models.TextChoices):
        NONE = "none", "بدون هوک"
        BUILDING = "building", "در حال ساخت"
        READY = "ready", "آماده"
        FAILED = "failed", "ناموفق"

    class VideoStyle(models.TextChoices):
        AUTO = "auto", "خودکار"
        MOTION = "motion", "موشن‌گرافیک"

    title = models.CharField(max_length=255, verbose_name="عنوان")
    body = models.TextField(verbose_name="متن محتوا")
    content_type = models.CharField(
        max_length=20, choices=ContentType.choices,
        default=ContentType.POST, verbose_name="نوع محتوا",
    )
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT, verbose_name="وضعیت تأیید",
    )
    idea = models.ForeignKey(
        ContentIdea, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="posts",
        verbose_name="ایدهٔ محتوا",
    )
    scheduled_at = models.DateTimeField(
        null=True, blank=True, verbose_name="زمان انتشار برنامه‌ریزی‌شده",
    )
    hashtags = models.TextField(blank=True, verbose_name="هشتگ‌ها")
    music_track = models.ForeignKey(
        MusicTrack, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="posts",
        verbose_name="موزیک",
    )
    image = models.ImageField(
        upload_to="publisher/%Y/%m/", blank=True, verbose_name="تصویر",
    )
    video = models.FileField(
        upload_to="publisher/%Y/%m/", blank=True, verbose_name="ویدیو",
    )
    hook_clip = models.FileField(
        upload_to="publisher/hooks/%Y/%m/", blank=True,
        verbose_name="کلیپ قلاب AI",
        help_text="کلیپ سینمایی ۸ ثانیه‌ای Veo که ابتدای ویدیوی نهایی قرار می‌گیرد",
    )
    hook_status = models.CharField(
        max_length=20, choices=HookStatus.choices,
        default=HookStatus.NONE, verbose_name="وضعیت هوک AI",
    )
    hook_error = models.CharField(
        max_length=500, blank=True, verbose_name="خطای ساخت هوک",
    )
    hook_provider = models.CharField(
        max_length=20, blank=True, verbose_name="موتور ساخت هوک",
        help_text="veo یا hf — موتوری که هوک فعلی را ساخته است",
    )
    hook_ready_at = models.DateTimeField(
        null=True, blank=True, verbose_name="زمان آماده‌شدن هوک",
    )
    link = models.URLField(blank=True, verbose_name="لینک")
    video_style = models.CharField(
        max_length=20, choices=VideoStyle.choices,
        default=VideoStyle.AUTO, verbose_name="سبک ویدیو",
        help_text="خودکار = اسلایدشو (+ هوک AI اگر آماده باشد)؛ موشن‌گرافیک = قالب متن/کارت متحرک بدون AI",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="publisher_posts",
        verbose_name="ایجادکننده",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        db_table = "publisher_post"
        verbose_name = "پست کانال"
        verbose_name_plural = "پست‌های کانال"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PublisherSettings(models.Model):
    """تنظیمات انتشار (Singleton) — کلیدهای ساخت هوک ویدیویی و اولویت موتورها."""

    veo_api_key = models.CharField(
        max_length=255, blank=True, verbose_name="کلید API ویدیو (Veo)",
        help_text="اگر خالی باشد، از کلید Gemini تنظیمات دستیار استفاده می‌شود.",
    )
    hf_token = models.CharField(
        max_length=255, blank=True, verbose_name="توکن Hugging Face",
        help_text="برای ساخت هوک رایگان با اسپیس Gradio — از huggingface.co → Settings → Access Tokens",
    )
    hf_space = models.CharField(
        max_length=255, blank=True, verbose_name="اسپیس Hugging Face",
        help_text="اگر خالی باشد، پیش‌فرض رله (ZeroCollabs/LTX-2.3-turbo) استفاده می‌شود.",
    )
    video_provider_priority = models.CharField(
        max_length=50, default="veo,hf", verbose_name="اولویت موتورهای ویدیو",
        help_text="ترتیب تلاش با ویرگول: veo (پولی، باکیفیت) و hf (رایگان)",
    )

    class Meta:
        db_table = "publisher_settings"
        verbose_name = "تنظیمات انتشار"
        verbose_name_plural = "تنظیمات انتشار"

    def __str__(self):
        return "تنظیمات انتشار"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass


class PublishJob(models.Model):
    """یک دستور انتشار یک پست روی یک یا چند پلتفرم."""

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        PROCESSING = "processing", "در حال پردازش"
        DONE = "done", "انجام شد"
        PARTIAL = "partial", "جزئی"
        FAILED = "failed", "ناموفق"

    post = models.ForeignKey(
        ChannelPost, on_delete=models.CASCADE, related_name="jobs",
        verbose_name="پست",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, verbose_name="وضعیت",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="publisher_jobs",
        verbose_name="ایجادکننده",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        db_table = "publisher_job"
        verbose_name = "کار انتشار"
        verbose_name_plural = "کارهای انتشار"
        ordering = ["-created_at"]

    def __str__(self):
        return f"انتشار «{self.post.title}» ({self.get_status_display()})"


class PublishLog(models.Model):
    """وضعیت ارسال یک کار روی یک پلتفرم — با retry نمایی."""

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        SENDING = "sending", "در حال ارسال"
        SUCCESS = "success", "موفق"
        FAILED = "failed", "ناموفق"

    job = models.ForeignKey(
        PublishJob, on_delete=models.CASCADE, related_name="logs",
        verbose_name="کار انتشار",
    )
    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name="publish_logs",
        verbose_name="پلتفرم",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, verbose_name="وضعیت",
    )
    response_data = models.JSONField(
        default=dict, blank=True, verbose_name="پاسخ خام سرویس",
    )
    error_message = models.TextField(blank=True, verbose_name="پیام خطا")
    attempt_count = models.PositiveIntegerField(default=0, verbose_name="تعداد تلاش")
    next_attempt_at = models.DateTimeField(
        null=True, blank=True, verbose_name="زمان تلاش بعدی",
    )
    external_message_id = models.CharField(
        max_length=255, blank=True, verbose_name="شناسه پیام در مقصد",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        db_table = "publisher_log"
        verbose_name = "لاگ انتشار"
        verbose_name_plural = "لاگ‌های انتشار"
        ordering = ["-created_at"]
        unique_together = [("job", "platform")]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]

    def __str__(self):
        return f"{self.platform.name} — {self.get_status_display()}"


class ContentInsight(models.Model):
    """آمار عملکرد یک پست منتشرشده در اینستاگرام — توسط کامند fetch_ig_insights پر می‌شود."""

    log = models.OneToOneField(
        PublishLog, on_delete=models.CASCADE, related_name="insight",
        verbose_name="لاگ انتشار",
    )
    post = models.ForeignKey(
        ChannelPost, on_delete=models.CASCADE, related_name="insights",
        verbose_name="پست",
    )
    reach = models.PositiveIntegerField(default=0, verbose_name="ریچ")
    likes = models.PositiveIntegerField(default=0, verbose_name="لایک")
    comments = models.PositiveIntegerField(default=0, verbose_name="کامنت")
    shares = models.PositiveIntegerField(default=0, verbose_name="اشتراک‌گذاری")
    saved = models.PositiveIntegerField(default=0, verbose_name="ذخیره")
    views = models.PositiveIntegerField(default=0, verbose_name="بازدید (plays برای ریل)")
    raw = models.JSONField(default=dict, blank=True, verbose_name="پاسخ خام اینسایت")
    fetched_at = models.DateTimeField(auto_now=True, verbose_name="زمان دریافت")

    class Meta:
        db_table = "publisher_content_insight"
        verbose_name = "آمار پست"
        verbose_name_plural = "آمار پست‌ها"
        ordering = ["-fetched_at"]

    def __str__(self):
        return f"آمار «{self.post.title}» (ریچ {self.reach})"
