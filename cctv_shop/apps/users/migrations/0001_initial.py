"""
Migration: users app — 0001_initial (email-based auth)
جداول: users_user, users_profile
"""
import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, verbose_name="superuser status")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="ایمیل")),
                ("first_name", models.CharField(blank=True, max_length=100, verbose_name="نام")),
                ("last_name", models.CharField(blank=True, max_length=100, verbose_name="نام خانوادگی")),
                ("phone", models.CharField(blank=True, help_text="اختیاری", max_length=15, verbose_name="شماره موبایل")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("is_staff", models.BooleanField(default=False, verbose_name="کارمند")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="تاریخ عضویت")),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={"verbose_name": "کاربر", "verbose_name_plural": "کاربران", "db_table": "users_user", "ordering": ["-date_joined"]},
            managers=[("objects", django.contrib.auth.models.BaseUserManager())],
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("user_type", models.CharField(choices=[("public", "مشتری عمومی"), ("partner", "مشتری همکار")], default="public", max_length=10, verbose_name="نوع کاربر")),
                ("company_name", models.CharField(blank=True, max_length=255, verbose_name="نام شرکت / برند")),
                ("national_id", models.CharField(blank=True, max_length=20, verbose_name="کد ملی / شناسه ملی")),
                ("is_approved", models.BooleanField(default=False, help_text="ادمین باید این را دستی فعال کند", verbose_name="تأیید همکار")),
                ("credit_limit", models.PositiveBigIntegerField(default=0, verbose_name="سقف اعتبار (تومان)")),
                ("address", models.TextField(blank=True, verbose_name="آدرس")),
                ("notes", models.TextField(blank=True, verbose_name="یادداشت ادمین")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL, verbose_name="کاربر")),
            ],
            options={"verbose_name": "پروفایل کاربر", "verbose_name_plural": "پروفایل‌های کاربران", "db_table": "users_profile"},
        ),
    ]
