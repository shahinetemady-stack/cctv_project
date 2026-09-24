from django.conf import settings
from django.db import models

from apps.core.models import AuditableModel, TimeStampedModel


class PayrollProfile(AuditableModel, TimeStampedModel):
    """پروفایل حقوقی هر پرسنل — ماژول‌های فعال و مبالغ پایه."""

    staff = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="payroll_profile", verbose_name="پرسنل",
    )
    # ── ماژول‌ها (فعال/غیرفعال به ازای هر کارمند) ──
    has_base_salary = models.BooleanField(default=True, verbose_name="حقوق ثابت")
    has_commission_personal = models.BooleanField(default=False, verbose_name="پورسانت فروش شخصی")
    has_commission_total = models.BooleanField(default=False, verbose_name="سهم از فروش کل مجموعه")
    has_bonus_penalty = models.BooleanField(default=False, verbose_name="تشویقی و تنبیه دستی")
    has_annual_bonus = models.BooleanField(default=False, verbose_name="عیدی و پاداش پایان سال")
    has_leave_management = models.BooleanField(default=False, verbose_name="مدیریت مرخصی")


    # ── مبالغ و نرخ‌ها (زیر تیک همان ماژول در پروفایل) ──
    base_amount = models.PositiveBigIntegerField(
        default=0, verbose_name="حقوق ثابت ماهانه (ریال)",
    )
    # عیدی
    annual_bonus_months = models.DecimalField(
        max_digits=3, decimal_places=1, default=2, verbose_name="مبنای عیدی (ماه حقوق)",
    )
    annual_bonus_formula = models.CharField(
        max_length=10, choices=[("legal", "قانون کار"), ("agreed", "توافقی")],
        default="legal", verbose_name="فرمول عیدی",
    )
    # مرخصی
    working_days_divisor = models.PositiveSmallIntegerField(
        default=30, verbose_name="مبنای روزهای ماه",
        help_text="حقوق روزانه = حقوق ثابت ÷ این عدد",
    )
    leave_entitled_days_per_month = models.DecimalField(
        max_digits=4, decimal_places=2, default=2.5, verbose_name="مرخصی استحقاقی ماهانه (روز)",
        # فعلاً صرفاً نگهداری/نمایش است — در محاسبه کسر مرخصی (services.recalculate_payslip) استفاده نمی‌شود
    )
    leave_sick_days_per_month = models.DecimalField(
        max_digits=4, decimal_places=2, default=1, verbose_name="سقف مرخصی استعلاجی ماهانه (روز)",
    )
    # پلکان پورسانت فروش شخصی — پیش‌رونده با بازه و درصد هر گام
    personal_commission_tiers = models.JSONField(
        default=list, blank=True, verbose_name="پلکان پورسانت فروش شخصی",
        help_text="لیستی از {from, to, step, percent} — روی فروش شخصی ماه اعمال می‌شود",
    )
    # پلکان سهم فروش کل مجموعه
    total_share_tiers = models.JSONField(
        default=list, blank=True, verbose_name="پلکان سهم فروش مجموعه",
        help_text="لیستی از {from, to, step, percent} — روی فروش کل ماه مجموعه اعمال می‌شود",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        db_table = "payroll_profile"
        verbose_name = "پروفایل حقوقی"
        verbose_name_plural = "پروفایل‌های حقوقی"

    def __str__(self):
        return f"پروفایل حقوقی {self.staff.get_full_name() or self.staff.phone}"


class LeaveRecord(AuditableModel, TimeStampedModel):
    """ثبت مرخصی روزانه پرسنل — مبنای کسر از حقوق."""

    class LeaveType(models.TextChoices):
        ENTITLED = "entitled", "استحقاقی"
        SICK = "sick", "استعلاجی"
        UNPAID = "unpaid", "بدون حقوق"

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="leave_records", verbose_name="پرسنل",
    )
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices, verbose_name="نوع مرخصی")
    date = models.DateField(verbose_name="تاریخ شروع")
    days_count = models.DecimalField(max_digits=4, decimal_places=1, verbose_name="تعداد روز")
    reason = models.CharField(max_length=200, blank=True, verbose_name="توضیح")

    class Meta:
        db_table = "payroll_leave_record"
        verbose_name = "مرخصی"
        verbose_name_plural = "مرخصی‌ها"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.staff.get_full_name() or self.staff.phone} — {self.get_leave_type_display()} {self.days_count} روز"


class BonusPenaltyRecord(AuditableModel, TimeStampedModel):
    """تشویقی (مثبت) یا تنبیه (منفی) دستی به تفکیک تاریخ — چند رکورد در ماه مجاز."""

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="bonus_penalty_records", verbose_name="پرسنل",
    )
    date = models.DateField(verbose_name="تاریخ")
    amount = models.BigIntegerField(
        verbose_name="مبلغ (ریال)",
        help_text="مثبت = تشویقی، منفی = تنبیه",
    )
    note = models.CharField(max_length=200, blank=True, verbose_name="توضیح")

    class Meta:
        db_table = "payroll_bonus_penalty"
        verbose_name = "تشویقی/تنبیه"
        verbose_name_plural = "تشویقی/تنبیه‌ها"
        ordering = ["-date"]

    def __str__(self):
        kind = "تشویقی" if self.amount >= 0 else "تنبیه"
        return f"{self.staff.get_full_name() or self.staff.phone} — {kind} {self.amount}"


class Payslip(AuditableModel, TimeStampedModel):
    """فیش حقوقی ماهانه — محاسبه ایدمپوتنت، قفل پس از paid."""

    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        CONFIRMED = "confirmed", "تأیید شده"
        PAID = "paid", "پرداخت شده"

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="payslips", verbose_name="پرسنل",
    )
    year = models.PositiveSmallIntegerField(verbose_name="سال (میلادی)")
    month = models.PositiveSmallIntegerField(verbose_name="ماه (میلادی)")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    # اجزای حقوق (ریال)
    base_amount = models.BigIntegerField(default=0, verbose_name="حقوق ثابت")
    personal_commission_amount = models.BigIntegerField(default=0, verbose_name="پورسانت فروش شخصی")
    total_sales_share_amount = models.BigIntegerField(default=0, verbose_name="سهم فروش مجموعه")
    bonus_penalty_amount = models.BigIntegerField(default=0, verbose_name="تشویقی/تنبیه")
    annual_bonus_amount = models.BigIntegerField(default=0, verbose_name="عیدی/پاداش")
    leave_deduction = models.BigIntegerField(default=0, verbose_name="کسر مرخصی بدون حقوق")
    gross_amount = models.BigIntegerField(default=0, verbose_name="ناخالص")
    net_amount = models.BigIntegerField(default=0, verbose_name="خالص")

    # ریز مرخصی ماه
    entitled_used = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="استحقاقی استفاده‌شده (روز)")
    sick_used = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="استعلاجی استفاده‌شده (روز)")
    unpaid_used = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="بدون حقوق (روز)")

    # آمار فروش ماه (برای نمایش در فیش)
    personal_sales = models.BigIntegerField(default=0, verbose_name="فروش شخصی ماه (ریال)")
    total_sales = models.BigIntegerField(default=0, verbose_name="فروش کل ماه (ریال)")

    payment = models.OneToOneField(
        "accounting.Payment", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payslip", verbose_name="سند پرداخت",
    )
    paid_amount = models.BigIntegerField(default=0, verbose_name="مجموع پرداخت‌شده (ریال)")
    accrual_payment = models.OneToOneField(
        "accounting.Payment", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payslip_accrual",
        verbose_name="سند هزینه/بدهی سر ماه",
    )
    notes = models.TextField(blank=True, verbose_name="یادداشت")

    class Meta:
        db_table = "payroll_payslip"
        verbose_name = "فیش حقوقی"
        verbose_name_plural = "فیش‌های حقوقی"
        ordering = ["-year", "-month", "staff__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["staff", "year", "month"], name="uniq_payslip_staff_month"),
        ]

    def __str__(self):
        return f"فیش {self.staff.get_full_name() or self.staff.phone} — {self.year}/{self.month:02d}"

    @property
    def remaining_amount(self):
        return max(0, self.net_amount - self.paid_amount)


class PayslipPayment(AuditableModel):
    """هر پرداخت (کامل یا قسطی) حقوق — لینک سند حسابداری به فیش."""

    payslip = models.ForeignKey(
        Payslip, on_delete=models.CASCADE, related_name="installments",
        verbose_name="فیش حقوقی",
    )
    payment = models.OneToOneField(
        "accounting.Payment", on_delete=models.PROTECT, related_name="payslip_installment",
        verbose_name="سند پرداخت",
    )
    amount = models.BigIntegerField(verbose_name="مبلغ (ریال)")

    class Meta:
        db_table = "payroll_payslip_payment"
        verbose_name = "پرداخت حقوق"
        verbose_name_plural = "پرداخت‌های حقوق"

    def __str__(self):
        return f"پرداخت {self.amount:,} ریال — {self.payslip}"
