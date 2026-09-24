from django.db import models


class FAQ(models.Model):
    """پرسش و پاسخ‌های آموزشی ربات — از پنل ادمین مدیریت می‌شود و در کانتکست مدل تزریق می‌گردد."""

    question = models.CharField(max_length=300, verbose_name="پرسش")
    answer   = models.TextField(verbose_name="پاسخ")
    keywords = models.CharField(
        max_length=300, blank=True, verbose_name="کلیدواژه‌ها",
        help_text="با ویرگول جدا کنید — برای تطبیق بهتر با سؤال مشتری (مثل: ارسال، پیک، تیپاکس)",
    )
    is_active  = models.BooleanField(default=True, verbose_name="فعال")
    order      = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        db_table = "assistant_faq"
        verbose_name = "پرسش و پاسخ"
        verbose_name_plural = "پرسش‌های متداول (آموزش ربات)"
        ordering = ["order", "id"]

    def __str__(self):
        return self.question


class AssistantSettings(models.Model):
    """تنظیمات ربات هوشمند (Singleton) — موتور اصلی قابل انتخاب + فالبک زنجیره‌ای تا Qwen لوکال."""

    PROVIDERS = [
        ("gemini",     "Google Gemini"),
        ("modelscope", "ModelScope — Qwen3 ابری (رایگان)"),
        ("zai",        "z.ai — GLM-4.5-Flash (رایگان)"),
        ("deepseek",   "DeepSeek (ارزان)"),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDERS, default="modelscope",
        verbose_name="موتور اصلی",
        help_text="اول این موتور جواب می‌دهد؛ اگر خطا داد، موتورهای دیگری که کلید دارند و در نهایت Qwen لوکال جایگزین می‌شوند.")

    gemini_api_key  = models.CharField(max_length=200, blank=True, verbose_name="کلید API جمینای",
        help_text="از Google AI Studio بگیرید. اگر خالی باشد، فقط Qwen لوکال جواب می‌دهد.")
    gemini_model    = models.CharField(max_length=50, default="gemini-3.6-flash", verbose_name="مدل جمینای")
    gemini_enabled  = models.BooleanField(default=True, verbose_name="جمینای فعال باشد",
        help_text="اول جمینای جواب می‌دهد؛ اگر خطا بدهد یا خاموش باشد، Qwen لوکال جایگزین می‌شود.")
    gemini_proxy    = models.CharField(max_length=200, blank=True, verbose_name="پروکسی برای جمینای",
        help_text="سرور ایران به گوگل دسترسی ندارد — پروکسی خارجی لازم است. مثال: socks5://127.0.0.1:1080 یا http://user:pass@ip:port")

    ms_api_key  = models.CharField(max_length=200, blank=True, verbose_name="کلید ModelScope",
        help_text="از modelscope.cn ← Access Token بگیرید — رایگان، بدون نیاز به پروکسی.")
    ms_model    = models.CharField(max_length=100, default="Qwen/Qwen3-32B", verbose_name="مدل ModelScope")
    zai_api_key = models.CharField(max_length=200, blank=True, verbose_name="کلید z.ai",
        help_text="از z.ai ← API Keys بگیرید — رایگان، بدون نیاز به پروکسی.")
    zai_model   = models.CharField(max_length=100, default="glm-4.5-flash", verbose_name="مدل z.ai")
    ds_api_key  = models.CharField(max_length=200, blank=True, verbose_name="کلید DeepSeek",
        help_text="از platform.deepseek.com بگیرید — نیازمند شارژ حساب (بسیار ارزان).")
    ds_model    = models.CharField(max_length=100, default="deepseek-chat", verbose_name="مدل DeepSeek")

    learn_from_gemini = models.BooleanField(default=True, verbose_name="یادگیری از پاسخ‌های هوش مصنوعی ابری",
        help_text="پاسخ‌های موتورهای ابری ذخیره می‌شوند و در پرامپت سؤال‌های مشابه بعدی تزریق می‌گردند.")

    class Meta:
        db_table = "assistant_settings"
        verbose_name = "تنظیمات ربات هوشمند"
        verbose_name_plural = "تنظیمات ربات هوشمند"

    def __str__(self):
        return "تنظیمات ربات هوشمند"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass


class LearnedQA(models.Model):
    """سؤال‌وجواب‌هایی که ربات از پاسخ‌های جمینای یاد گرفته — در کانتکست سؤال‌های مشابه تزریق می‌شوند."""

    question   = models.CharField(max_length=300, verbose_name="سؤال مشتری")
    answer     = models.TextField(verbose_name="پاسخ یادگرفته‌شده")
    engine     = models.CharField(max_length=20, default="gemini", verbose_name="موتور پاسخ‌دهنده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ یادگیری")

    class Meta:
        db_table = "assistant_learned_qa"
        verbose_name = "پاسخ یادگرفته‌شده"
        verbose_name_plural = "پاسخ‌های یادگرفته‌شده از هوش مصنوعی ابری"
        ordering = ["-id"]

    def __str__(self):
        return self.question
