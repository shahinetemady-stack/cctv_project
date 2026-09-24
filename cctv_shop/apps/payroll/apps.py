from django.apps import AppConfig


class PayrollConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payroll"
    verbose_name = "حقوق و دستمزد"

    def ready(self):
        from . import signals  # noqa: F401 — ثبت سیگنال‌های ساخت طرف‌حساب پرسنل
