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

        today = timezone.localdate()
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

    class Title(models.TextChoices):
        MR = "mr", "آقای"
        MRS = "mrs", "خانم"
        COMPANY = "company", "شرکت"
        SHOP = "shop", "فروشگاه"

    title = models.CharField(max_length=10, choices=Title.choices, blank=True, verbose_name="عنوان")

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name="کاربر"
    )
    user_type = models.CharField(
        max_length=10, choices=UserType.choices, default=UserType.PUBLIC, verbose_name="نوع کاربر"
    )
    company_name = models.CharField(max_length=255, blank=True, verbose_name="نام فروشگاه / شرکت")
    national_id = models.CharField(max_length=20, blank=True, verbose_name="کد ملی / شناسه ملی")
    social_url = models.CharField(
        max_length=255, blank=True, verbose_name="اینستاگرام / کانال تلگرام",
        help_text="برای نصاب‌های مستقل — احراز فعالیت در حوزه دوربین",
    )
    document = models.ImageField(
        upload_to="partner_docs/%Y/%m/", blank=True, verbose_name="مدرک همکاری",
        help_text="تصویر کارت ویزیت یا عکس صفحه ادمین پیج — برای احراز نصاب‌های فریلنسر",
    )
    has_fx = models.BooleanField(default=False, verbose_name="عملیات ارزی",
        help_text="اگر فعال باشد، ستون‌ها و فیلدهای ارزی (یوان) برای این طرف حساب نمایش داده می‌شود")
    is_approved = models.BooleanField(
        default=False, verbose_name="تأیید همکار",
        help_text="ادمین باید این را دستی فعال کند",
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, verbose_name="زمان تأیید همکار",
        help_text="فقط در لحظه تأیید درخواست همکاری ست می‌شود — با ویرایش پروفایل تغییر نمی‌کند",
    )
    partner_tier = models.CharField(
        max_length=10, blank=True,
        choices=[("silver", "همکار سیلور"), ("gold", "همکار گلد"), ("platinum", "همکار پلاتینیوم")],
        verbose_name="سطح همکار",
        help_text="قیمت‌نمایشی سایت بر اساس سطح: سیلور=یکماهه، گلد=تو حسابی، پلاتینیوم=تو حسابی + گزینه نقدی/یکماهه",
    )
    credit_limit = models.PositiveBigIntegerField(
        default=0, verbose_name="سقف اعتبار (ریال)",
        help_text="۰ = نامحدود. اگر مجموع بدهی (حساب باز، چک وصول‌نشده، ردیف‌های تسویه باز) از این سقف بگذرد، فروش اعتباری جدید بسته می‌شود",
    )
    legacy_purchase_total = models.PositiveBigIntegerField(
        default=0, verbose_name="سابقه خرید قبلی خارج از سایت (ریال)",
        help_text="مجموع خریدهای سنتی/حضوری قبل از سایت به ریال — با خریدهای آنلاین جمع می‌شود و ملاک ارتقای سطح همکار است",
    )
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
    restriction_override = models.BooleanField(
        default=False, verbose_name="باز کردن دستی محدودیت",
        help_text="اگر فعال باشد، محدودیت‌های خودکار معوقات (فقط نقدی / مسدود) برای این کاربر اعمال نمی‌شود",
    )
    payment_credit_irr = models.PositiveBigIntegerField(
        default=0, verbose_name="بستانکاری نقدی (ریال)",
        help_text="اضافه‌واریزی‌های مشتری — به‌صورت خودکار به بدهی‌های بعدی او تخصیص می‌یابد",
    )
    notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    club_near_notified_at = models.DateTimeField(
        null=True, blank=True, verbose_name="آخرین اطلاع‌رسانی نزدیکی به آستانه",
    )
    club_risk_snoozed_until = models.DateTimeField(
        null=True, blank=True, verbose_name="عدم نمایش هشدار تنزل سطح تا",
        help_text="ادمین می‌تواند هشدار تنزل یک همکار را موقتاً (مثلاً یک ماه) پنهان کند",
    )
    platinum_auto_granted = models.BooleanField(
        default=False, verbose_name="پلاتینیوم اعطاشده به‌صورت خودکار",
        help_text="وقتی ارزیابی خودکار کاربر را پلاتینیوم کند فعال می‌شود؛ تا تعیین سقف اعتبار، فاکتور اعتباری (توحسابی) برایش صادر نمی‌شود. با تغییر دستی سطح پاک می‌شود",
    )
    parent_account = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="linked_accounts", verbose_name="حساب اصلی",
        help_text="برای شرکای یک کسب‌وکار: این کاربر با موبایل خودش وارد می‌شود "
        "ولی همه داده‌ها/سفارش‌ها روی حساب اصلی ثبت و دیده می‌شود",
    )
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


class PartnerClubSettings(models.Model):
    """تنظیمات باشگاه همکاران — آستانه‌های ارتقای سطح (ریال). سینگلتون (pk=1)."""

    silver_to_gold_amount = models.PositiveBigIntegerField(
        default=500_000_000, verbose_name="حداقل مجموع خرید برای ارتقا سیلور → گلد (ریال)",
    )
    gold_to_platinum_amount = models.PositiveBigIntegerField(
        default=2_000_000_000, verbose_name="حداقل مجموع خرید برای ارتقا گلد → پلاتینیوم (ریال)",
    )
    period_months = models.PositiveSmallIntegerField(
        default=3, verbose_name="بازه محاسبه خرید آنلاین (ماه)",
        help_text="خریدهای آنلاین این چند ماه اخیر + سابقه خرید قبلی، ملاک ارتقا است",
    )
    auto_evaluate_enabled = models.BooleanField(
        default=True, verbose_name="ارزیابی خودکار روزانه سطوح",
    )
    overdue_warn_workdays = models.PositiveSmallIntegerField(
        default=3, verbose_name="مهلت هشدار معوقات (روز کاری)",
        help_text="تا این تعداد روز کاری پس از سررسید فقط هشدار می‌رود (جمعه و تعطیلات رسمی حساب نمی‌شوند)",
    )
    overdue_cash_only_days = models.PositiveSmallIntegerField(
        default=7, verbose_name="مهلت خرید فقط نقدی (روز تقویمی)",
        help_text="پس از پایان مهلت هشدار، تا این تعداد روز فقط خرید نقدی ممکن است؛ بعد از آن ثبت سفارش کاملاً بسته می‌شود",
    )
    tier_benefits_silver = models.TextField(blank=True, verbose_name="توضیح مزایای سطح سیلور")
    tier_benefits_gold = models.TextField(blank=True, verbose_name="توضیح مزایای سطح گلد")
    tier_benefits_platinum = models.TextField(blank=True, verbose_name="توضیح مزایای سطح پلاتینیوم")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_partner_club_settings"
        verbose_name = "تنظیمات باشگاه همکاران"
        verbose_name_plural = "تنظیمات باشگاه همکاران"

    def __str__(self):
        return "تنظیمات باشگاه همکاران"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class PartnerGuarantee(TimeStampedModel):
    """تضامین گرفته‌شده از همکار برای فروش اعتباری — ثبت توسط ادمین."""

    class GuaranteeType(models.TextChoices):
        CHECK = "check", "چک"
        PROMISSORY = "promissory", "سفته"
        ID_CARD = "id_card", "کارت ملی"
        PROPERTY_DEED = "property_deed", "سند ملکی"
        INTRODUCTION = "introduction", "معرفی‌نامه کسبه"
        OTHER = "other", "سایر"

    profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="guarantees", verbose_name="همکار",
    )
    contact = models.ForeignKey(
        'accounting.Contact', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="guarantees", verbose_name="طرف حساب دستی",
        help_text="برای طرف حساب‌هایی که کاربر سایت ندارند",
    )
    guarantee_type = models.CharField(
        max_length=20, choices=GuaranteeType.choices, verbose_name="نوع تضمین",
    )
    amount_rials = models.PositiveBigIntegerField(
        default=0, verbose_name="مبلغ (ریال)",
        help_text="مبلغ اسمی چک/سفته — برای تضامین غیرنقدی صفر بماند",
    )
    description = models.TextField(blank=True, verbose_name="توضیحات")
    document = models.ImageField(
        upload_to="partner_guarantees/%Y/%m/", blank=True, verbose_name="تصویر مدرک",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="registered_guarantees", verbose_name="ثبت‌کننده",
    )

    class Meta:
        db_table = "users_partner_guarantee"
        verbose_name = "تضمین همکار"
        verbose_name_plural = "تضامین همکاران"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_guarantee_type_display()} — {self.profile}"


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
    # دریافت و پرداخت
    ('payment_view',     'دریافت و پرداخت'),
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
    # حقوق و دستمزد
    ('payroll_view',     'مشاهده حقوق و دستمزد'),
    ('payroll_edit',     'تعریف و ویرایش حقوق پرسنل'),
    ('payroll_pay',      'محاسبه و پرداخت حقوق'),
    # هزینه‌ها
    ('expenses_view',    'مشاهده هزینه‌ها'),
    ('expenses_edit',    'ثبت و ویرایش هزینه‌ها'),
    # تولید (مونتاژ)
    ('production_view',   'مشاهده امور تولید'),
    ('production_manage', 'تعریف دستوره و اجرای مونتاژ'),
    # چت مشتریان
    ('chat_view',        'مشاهده چت مشتریان'),
    ('chat_reply',       'پاسخ به چت مشتریان'),
    # انتشار در پیام‌رسان‌ها
    ('publisher_view',        'مشاهده انتشار محتوا'),
    ('publisher_publish',     'ایجاد و انتشار محتوا در پیام‌رسان‌ها'),
    ('publisher_approve',     'تأیید/رد محتوای آماده انتشار'),
    ('publisher_credentials', 'مدیریت توکن پیام‌رسان‌ها'),
    # منوها
    ('pricelist_view',          'مشاهده لیست قیمت'),
    ('orders_view',             'مشاهده سفارشات'),
    ('aging_view',              'مطالبات تاریخ‌گذشته'),
    ('reject_report_view',      'گزارش رد سفارش‌ها'),
    ('warehouses_view',         'مشاهده انبارها'),
    ('content_view',            'مدیریت محتوای آموزشی'),
    ('packages_view',           'مدیریت پکیج‌ها'),
    ('backup_view',             'بک‌آپ سیستم'),
    ('category_fields_view',    'ویژگی‌های دسته‌ها'),
    ('categories_view',         'مدیریت دسته‌بندی محصولات'),
    ('shortage_view',           'گزارش مازاد تقاضا'),
    ('sms_settings_view',       'تنظیمات پیامک'),
    ('assistant_settings_view', 'ربات هوشمند'),
    ('club_settings_view',      'باشگاه همکاران'),
    ('sms_campaign_view',       'کمپین پیامکی'),
    ('leads_view',              'مخاطبان تبلیغاتی'),
    ('stats_view',              'آمار سایت'),
    ('services_view',           'سرویس‌ها و اشتراک‌ها'),
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

class PhoneChangeRequest(models.Model):
    """درخواست تغییر موبایل — چون هویت و همه داده‌ها روی موبایل است، تغییرش
    فقط با تأیید مدیر انجام می‌شود."""

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار تأیید"
        APPROVED = "approved", "تأیید شده"
        REJECTED = "rejected", "رد شده"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE,
                             related_name="phone_change_requests", verbose_name="کاربر")
    new_phone = models.CharField(max_length=11, verbose_name="موبایل جدید")
    reason = models.CharField(max_length=300, blank=True, verbose_name="دلیل")
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING, verbose_name="وضعیت")
    reviewed_by = models.ForeignKey("users.User", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="reviewed_phone_requests",
                                    verbose_name="بررسی‌کننده")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_phone_change_request"
        verbose_name = "درخواست تغییر موبایل"
        verbose_name_plural = "درخواست‌های تغییر موبایل"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} → {self.new_phone} ({self.get_status_display()})"


class ProfileChangeRequest(models.Model):
    """درخواست تغییر مشخصات هویتی (نام، شرکت، کد ملی و…) — مشتری نمی‌تواند
    مستقیم ویرایش کند؛ فقط با درخواست + تأیید مدیر اعمال می‌شود."""

    class Field(models.TextChoices):
        FIRST_NAME = "first_name", "نام"
        LAST_NAME = "last_name", "نام خانوادگی"
        COMPANY_NAME = "company_name", "نام شرکت"
        NATIONAL_ID = "national_id", "کد ملی"
        ADDRESS = "address", "آدرس"

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار تأیید"
        APPROVED = "approved", "تأیید شده"
        REJECTED = "rejected", "رد شده"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE,
                             related_name="profile_change_requests", verbose_name="کاربر")
    field = models.CharField(max_length=20, choices=Field.choices, verbose_name="فیلد")
    new_value = models.CharField(max_length=300, verbose_name="مقدار جدید")
    reason = models.CharField(max_length=300, blank=True, verbose_name="دلیل")
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING, verbose_name="وضعیت")
    reviewed_by = models.ForeignKey("users.User", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="reviewed_profile_requests",
                                    verbose_name="بررسی‌کننده")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_profile_change_request"
        verbose_name = "درخواست تغییر مشخصات"
        verbose_name_plural = "درخواست‌های تغییر مشخصات"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.get_field_display()} → {self.new_value} ({self.get_status_display()})"


def effective_user(user):
    """حساب مؤثر برای داده‌های مشتری‌محور — اگر کاربر شریکِ حساب دیگری باشد،
    حساب اصلی برمی‌گردد (همه سفارش‌ها/کارت‌ها روی همان ثبت و دیده می‌شوند)."""
    try:
        profile = user.profile
    except Exception:
        return user
    return profile.parent_account if profile and profile.parent_account_id else user


def accessible_user_ids(user):
    """شناسه‌های قابل مشاهده برای کاربر: حساب مؤثر + همه شرکای لینک‌شده به آن.
    برای نمایش تاریخچه (سفارش‌های قبل از لینک هم دیده شوند) — برای *ثبت* داده
    جدید فقط از effective_user استفاده کن."""
    eff = effective_user(user)
    ids = [eff.id]
    ids.extend(
        User.objects.filter(profile__parent_account=eff).values_list("id", flat=True)
    )
    return ids
