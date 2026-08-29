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
