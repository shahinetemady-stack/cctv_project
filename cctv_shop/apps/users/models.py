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

    def overdue_settlement_lines(self):
        """ردیف‌های تسویه سررسیدگذشتهٔ این کاربر (فاکتورهای غیرلغوشده با مانده > ۰)."""
        from django.utils import timezone
        from apps.accounting.models import SettlementLine

        today = timezone.now().date()
        lines = (
            SettlementLine.objects
            .filter(invoice__customer=self, due_date__lt=today, is_active=True)
            .exclude(invoice__status="cancelled")
            .select_related("invoice", "invoice__order")
            .prefetch_related("allocations")
            .order_by("due_date")
        )
        result = []
        for line in lines:
            paid = sum(a.amount for a in line.allocations.all())
            remaining = line.amount - paid
            if remaining <= 0:
                continue
            result.append({
                "id": line.id,
                "invoice_number": line.invoice.invoice_number,
                "order_number": line.invoice.order.order_number if line.invoice.order else None,
                "settlement_type": line.settlement_type,
                "amount": line.amount,
                "remaining": remaining,
                "due_date": line.due_date.isoformat(),
                "days_overdue": (today - line.due_date).days,
            })
        return result

    def overdue_total(self) -> int:
        """مجموع ماندهٔ سررسیدگذشته (ریال)."""
        return sum(item["remaining"] for item in self.overdue_settlement_lines())

    def overdue_count(self) -> int:
        """تعداد ردیف‌های تسویه سررسیدگذشته."""
        return len(self.overdue_settlement_lines())


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
    partner_tier = models.CharField(
        max_length=10, blank=True,
        choices=[("silver", "همکار سیلور"), ("gold", "همکار گلد"), ("platinum", "همکار پلاتینیوم")],
        verbose_name="سطح همکار",
        help_text="قیمت‌نمایشی سایت بر اساس سطح: سیلور=یکماهه، گلد=تو حسابی، پلاتینیوم=تو حسابی + گزینه نقدی/یکماهه",
    )
    credit_limit = models.PositiveBigIntegerField(default=0, verbose_name="سقف اعتبار (تومان)")
    opening_balance_irr = models.BigIntegerField(default=0, verbose_name="مانده اول دوره (ریال)",
                        help_text="مثبت = مشتری به ما بدهکار | منفی = ما به او بدهکاریم")
    opening_balance_cny = models.DecimalField(max_digits=18, decimal_places=2, default=0,
                        verbose_name="مانده اول دوره (یوان)",
                        help_text="مثبت = مشتری به ما بدهکار | منفی = ما به او بدهکاریم")
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="درصد تخفیف همکار",
        help_text="مثال: 15 یعنی ۱۵٪ تخفیف روی قیمت نهایی",
    )
    address = models.TextField(blank=True, verbose_name="آدرس")
    province = models.CharField(max_length=50, blank=True, verbose_name="استان")
    notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    linked_contact = models.ForeignKey(
        'accounting.Contact', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='linked_users',
        verbose_name="طرف حساب مرتبط",
        help_text="کاربر سایه‌ای که برای اتصال فاکتور فروش به این طرف حساب ساخته شده — در لیست مشتریان سایت دیده نمی‌شود",
    )

    class Meta:
        db_table = "users_profile"
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"

    def __str__(self):
        return f"پروفایل {self.user}"


class OtpCode(models.Model):
    """کد یکبارمصرف پیامکی — برای بازیابی رمز عبور / فعال‌سازی حساب‌های فروشگاهی.
    هش کد ذخیره می‌شود (نه خود کد) و پس از انقضا/استفاده حذف می‌شود."""
    phone      = models.CharField(max_length=11, db_index=True)
    code_hash  = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts   = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_otp_code"
        verbose_name = "کد یکبارمصرف"
        verbose_name_plural = "کدهای یکبارمصرف"

    def __str__(self):
        return f"OTP {self.phone} ({self.created_at:%H:%M})"


# ─── RBAC ────────────────────────────────────────────────────

PERMISSIONS = [
    # فروش
    ('sale_view',        'مشاهده فاکتورهای فروش'),
    ('sale_create',      'صدور فاکتور فروش'),
    ('sale_edit',        'ویرایش/حذف فاکتور فروش و دریافت‌ها'),
    ('sale_payment',     'ثبت پرداخت مشتری'),
    # برگشت از فروش و خرید
    ('return_view',      'مشاهده اسناد برگشت'),
    ('return_create',    'صدور سند برگشت'),
    ('return_edit',      'لغو سند برگشت'),
    # کاردکس و انبار
    ('kardex_view',      'مشاهده کاردکس'),
    ('kardex_edit',      'ثبت ورود/خروج موجودی'),
    # خرید
    ('purchase_view',    'مشاهده فاکتورهای خرید'),
    ('purchase_create',  'ثبت فاکتور خرید'),
    ('purchase_edit',    'ویرایش/حذف فاکتور خرید'),
    ('payment_edit',     'ویرایش/حذف دریافت و پرداخت'),
    # طرف حساب
    ('contacts_view',    'مشاهده طرف حساب‌ها'),
    ('contacts_create',  'افزودن طرف حساب'),
    ('contacts_edit',    'ویرایش طرف حساب‌ها'),
    ('partner_approve',  'تأیید همکار'),
    # گزارشات مالی
    ('reports_view',     'مشاهده گزارشات مالی'),
    ('balance_view',     'مشاهده تراز و سود/زیان'),
    ('accounts_edit',    'مدیریت بانک (ساخت/ویرایش/حذف حساب)'),
    # مدیریت کاربران
    ('users_view',       'مشاهده کاربران'),
    ('users_edit',       'ویرایش کاربران و نقش‌ها'),
    # تنظیمات
    ('exchange_rate_edit', 'ویرایش نرخ یوان روز'),
    # محصولات
    ('products_view',    'مشاهده محصولات'),
    ('products_edit',    'ویرایش محصولات'),
    # فرمول قیمت
    ('pricing_rate_view',  'مشاهده نرخ یوان در فرمول قیمت'),
    ('pricing_costs_view', 'مشاهده/ویرایش هزینه و سود دسته‌ها'),
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
    allowed_contact_types = models.JSONField(default=list, blank=True,
                    verbose_name="نوع‌های مجاز طرف حساب",
                    help_text="لیست کدهای نوع طرف حساب — خالی = همه نوع‌ها")
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


class ActivityLog(models.Model):
    """لاگ فعالیت‌ها — ورود/خروج و رویدادهای نوشتاری API (ثبت خودکار توسط میدل‌ور)."""

    class Action(models.TextChoices):
        LOGIN  = "login",  "ورود"
        LOGOUT = "logout", "خروج"
        CREATE = "create", "ایجاد"
        UPDATE = "update", "ویرایش"
        DELETE = "delete", "حذف"

    user       = models.ForeignKey(User, on_delete=models.SET_NULL,
                     null=True, blank=True, related_name="activity_logs", verbose_name="کاربر")
    action     = models.CharField(max_length=10, choices=Action.choices, verbose_name="رویداد")
    method     = models.CharField(max_length=8, verbose_name="متد")
    path       = models.CharField(max_length=300, verbose_name="مسیر")
    status     = models.PositiveSmallIntegerField(default=200, verbose_name="وضعیت پاسخ")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="زمان")

    class Meta:
        db_table = "users_activity_log"
        verbose_name = "لاگ فعالیت"
        verbose_name_plural = "لاگ فعالیت‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.get_action_display()} — {self.path}"
