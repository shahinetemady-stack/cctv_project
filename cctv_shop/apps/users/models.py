"""
apps/users/models.py
─────────────────────
Custom User model — ورود با ایمیل و رمز عبور.

دو نوع کاربر:
  PUBLIC  → مشتری عمومی، خرید مستقیم
  PARTNER → مشتری همکار، نیاز به تأیید ادمین
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """USERNAME_FIELD = email | احراز هویت: ایمیل + رمز عبور → JWT"""

    email = models.EmailField(unique=True, null=True, blank=True, verbose_name="ایمیل")
    first_name = models.CharField(max_length=100, blank=True, verbose_name="نام")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی")
    phone = models.CharField(
        max_length=15, unique=True, verbose_name="شماره موبایل",
        help_text="اجباری — با آن وارد شوید",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_staff = models.BooleanField(default=False, verbose_name="کارمند")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="تاریخ عضویت")

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        db_table = "users_user"
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        ordering = ["-date_joined"]

    def __str__(self):
           return self.phone or self.email or str(self.pk)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_partner(self):
        try:
            return (
                self.profile.user_type == UserProfile.UserType.PARTNER
                and self.profile.is_approved
            )
        except UserProfile.DoesNotExist:
            return False


class UserProfile(TimeStampedModel):
    """Extended profile. ادمین is_approved را برای PARTNER فعال می‌کند."""

    class UserType(models.TextChoices):
        PUBLIC = "public", "مشتری عمومی"
        PARTNER = "partner", "مشتری همکار"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name="کاربر"
    )
    user_type = models.CharField(
        max_length=10, choices=UserType.choices, default=UserType.PUBLIC, verbose_name="نوع کاربر"
    )
    company_name = models.CharField(max_length=255, blank=True, verbose_name="نام شرکت / برند")
    national_id = models.CharField(max_length=20, blank=True, verbose_name="کد ملی / شناسه ملی")
    is_approved = models.BooleanField(
        default=False, verbose_name="تأیید همکار",
        help_text="ادمین باید این را دستی فعال کند",
    )
    credit_limit = models.PositiveBigIntegerField(default=0, verbose_name="سقف اعتبار (تومان)")
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="درصد تخفیف همکار",
        help_text="مثال: 15 یعنی ۱۵٪ تخفیف روی قیمت نهایی",
    )
    address = models.TextField(blank=True, verbose_name="آدرس")
    notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")

    class Meta:
        db_table = "users_profile"
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"

    def __str__(self):
        return f"پروفایل {self.user}"
