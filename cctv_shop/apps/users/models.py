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


# ─── RBAC ────────────────────────────────────────────────────

PERMISSIONS = [
    # فروش
    ('sale_view',        'مشاهده فاکتورهای فروش'),
    ('sale_create',      'صدور فاکتور فروش'),
    ('sale_payment',     'ثبت پرداخت مشتری'),
    # کاردکس و انبار
    ('kardex_view',      'مشاهده کاردکس'),
    ('kardex_edit',      'ثبت ورود/خروج موجودی'),
    # خرید
    ('purchase_view',    'مشاهده فاکتورهای خرید'),
    ('purchase_create',  'ثبت فاکتور خرید'),
    # طرف حساب
    ('contacts_view',    'مشاهده طرف حساب‌ها'),
    ('contacts_edit',    'ویرایش طرف حساب‌ها'),
    # گزارشات مالی
    ('reports_view',     'مشاهده گزارشات مالی'),
    ('balance_view',     'مشاهده تراز و سود/زیان'),
    # مدیریت کاربران
    ('users_view',       'مشاهده کاربران'),
    ('users_edit',       'ویرایش کاربران و نقش‌ها'),
    # محصولات
    ('products_view',    'مشاهده محصولات'),
    ('products_edit',    'ویرایش محصولات'),
    # داشبورد
    ('dashboard_view',   'مشاهده داشبورد'),
]

PERMISSION_CHOICES = [(k, v) for k, v in PERMISSIONS]


class Role(models.Model):
    """نقش کاربری"""
    name        = models.CharField(max_length=50, unique=True, verbose_name="نام نقش")
    description = models.CharField(max_length=200, blank=True, verbose_name="توضیح")
    permissions = models.JSONField(default=list, verbose_name="دسترسی‌ها",
                    help_text="لیست کدهای دسترسی")
    is_active   = models.BooleanField(default=True, verbose_name="فعال")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_role"
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def has_perm(self, perm_code):
        return perm_code in self.permissions

    def perm_count(self):
        return len(self.permissions)


class StaffProfile(models.Model):
    """پروفایل پرسنل — نقش و دسترسی"""
    user       = models.OneToOneField(User, on_delete=models.CASCADE,
                    related_name="staff_profile", verbose_name="کاربر")
    role       = models.ForeignKey(Role, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name="staff_members",
                    verbose_name="نقش")
    employee_id = models.CharField(max_length=20, blank=True, verbose_name="کد پرسنلی")
    department  = models.CharField(max_length=100, blank=True, verbose_name="بخش")
    is_active   = models.BooleanField(default=True, verbose_name="فعال")
    note        = models.TextField(blank=True, verbose_name="توضیحات")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_staff_profile"
        verbose_name = "پرسنل"
        verbose_name_plural = "پرسنل"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.phone} — {self.role}"

    def has_perm(self, perm_code):
        """چک دسترسی — superuser همه چیز دارد"""
        if self.user.is_superuser:
            return True
        if not self.role or not self.role.is_active:
            return False
        return self.role.has_perm(perm_code)
