from django.conf import settings
from django.db import models

from apps.core.models import AuditableModel, TimeStampedModel


class ExpenseCategory(AuditableModel, TimeStampedModel):
    """سر فصل هزینه — قابل تعریف توسط کاربر، در یکی از دو دسته."""

    class CategoryType(models.TextChoices):
        RECURRING = "recurring", "هزینه تکرارشونده"
        GENERAL = "general", "هزینه متفرقه"

    name = models.CharField(max_length=100, unique=True, verbose_name="نام سر فصل")
    category_type = models.CharField(max_length=10, choices=CategoryType.choices,
                                     verbose_name="دسته")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        db_table = "expense_category"
        verbose_name = "سر فصل هزینه"
        verbose_name_plural = "سر فصل‌های هزینه"
        ordering = ["category_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class RecurringExpense(AuditableModel, TimeStampedModel):
    """هزینه تکرارشونده ماهانه با مبلغ ثابت (مثل اجاره مغازه)."""

    title = models.CharField(max_length=150, verbose_name="عنوان")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT,
                                 related_name="recurring_expenses", verbose_name="سر فصل")
    monthly_amount = models.PositiveBigIntegerField(verbose_name="مبلغ ماهانه (ریال)")
    contact = models.ForeignKey("accounting.Contact", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="recurring_expenses",
                                verbose_name="طرف حساب پرداخت (اختیاری)")
    deposit_amount = models.PositiveBigIntegerField(
        default=0, verbose_name="پول پیش / ودیعه (ریال)",
        help_text="صرفاً برای اطلاع — در محاسبات ماهانه لحاظ نمی‌شود",
    )
    start_date = models.DateField(verbose_name="شروع از")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        db_table = "expense_recurring"
        verbose_name = "هزینه تکرارشونده"
        verbose_name_plural = "هزینه‌های تکرارشونده"

    def __str__(self):
        return f"{self.title} — {self.monthly_amount:,} ریال/ماه"


class ExpenseCharge(AuditableModel, TimeStampedModel):
    """هزینه ثبت‌شده یک ماه (از هر سه منبع) — با سند بدهی و پرداخت قسطی.

    منبع: تکرارشونده (recurring) / متفرقه (general) / سود مشارکت (investor).
    """

    class Source(models.TextChoices):
        RECURRING = "recurring", "تکرارشونده"
        GENERAL = "general", "متفرقه"
        INVESTOR = "investor", "سود مشارکت"

    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        CONFIRMED = "confirmed", "تأیید شده"
        PAID = "paid", "پرداخت شده"

    source = models.CharField(max_length=10, choices=Source.choices)
    title = models.CharField(max_length=200, verbose_name="عنوان")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="charges",
                                 verbose_name="سر فصل")
    recurring = models.ForeignKey(RecurringExpense, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name="charges",
                                  verbose_name="هزینه تکرارشونده")
    investor = models.ForeignKey("Investor", on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="profit_charges",
                                 verbose_name="سرمایه‌گذار")
    contact = models.ForeignKey("accounting.Contact", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="expense_charges",
                                verbose_name="طرف حساب پرداخت")
    year = models.PositiveSmallIntegerField(verbose_name="سال (میلادی)")
    month = models.PositiveSmallIntegerField(verbose_name="ماه (میلادی)")
    date = models.DateField(verbose_name="تاریخ هزینه", help_text="تعیین‌کننده ماه جلالی نمایش")
    amount = models.BigIntegerField(default=0, verbose_name="مبلغ (ریال)")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    paid_amount = models.BigIntegerField(default=0, verbose_name="پرداخت‌شده (ریال)")
    accrual_payment = models.OneToOneField(
        "accounting.Payment", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="expense_accrual",
        verbose_name="سند هزینه/بدهی",
    )
    payment = models.OneToOneField(
        "accounting.Payment", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="expense_charge",
        verbose_name="آخرین سند پرداخت",
    )
    notes = models.TextField(blank=True, verbose_name="یادداشت")

    class Meta:
        db_table = "expense_charge"
        verbose_name = "هزینه ماهانه"
        verbose_name_plural = "هزینه‌های ماهانه"
        ordering = ["-year", "-month", "id"]
        constraints = [
            models.UniqueConstraint(fields=["recurring", "year", "month"],
                                    name="uniq_charge_recurring_month"),
            models.UniqueConstraint(fields=["investor", "year", "month"],
                                    name="uniq_charge_investor_month"),
        ]

    def __str__(self):
        return f"{self.title} — {self.year}/{self.month:02d}"

    @property
    def remaining_amount(self):
        return max(0, self.amount - self.paid_amount)


class Investor(AuditableModel, TimeStampedModel):
    """سرمایه‌گذار مشارکت — اصل سرمایه روزشمار و سود ماهانه درصدی."""

    contact = models.OneToOneField("accounting.Contact", on_delete=models.PROTECT,
                                   related_name="investor", verbose_name="طرف حساب")
    annual_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0,
                                      verbose_name="نرخ سود سالانه (٪)")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        db_table = "expense_investor"
        verbose_name = "سرمایه‌گذار"
        verbose_name_plural = "سرمایه‌گذاران"

    def __str__(self):
        return f"{self.contact.name} — {self.annual_rate}٪ سالانه"

    @property
    def principal(self):
        """اصل سرمایه فعلی = مجموع واریزها − برداشت‌ها (ریال)."""
        from django.db.models import Sum
        s = self.movements.aggregate(total=Sum("amount"))["total"]
        return int(s) if s else 0


class InvestorMovement(AuditableModel, TimeStampedModel):
    """گردش اصل سرمایه: واریز (positive) / برداشت (negative) — با سند نقدی."""

    class MovementType(models.TextChoices):
        DEPOSIT = "deposit", "واریز سرمایه"
        WITHDRAW = "withdraw", "برداشت سرمایه"

    investor = models.ForeignKey(Investor, on_delete=models.CASCADE,
                                 related_name="movements", verbose_name="سرمایه‌گذار")
    movement_type = models.CharField(max_length=10, choices=MovementType.choices,
                                     verbose_name="نوع")
    date = models.DateField(verbose_name="تاریخ")
    amount = models.PositiveBigIntegerField(verbose_name="مبلغ (ریال)")
    account = models.ForeignKey("accounting.Account", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="investor_movements",
                                verbose_name="حساب (اختیاری)")
    note = models.CharField(max_length=200, blank=True, verbose_name="توضیح")

    class Meta:
        db_table = "expense_investor_movement"
        verbose_name = "گردش سرمایه"
        verbose_name_plural = "گردش‌های سرمایه"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.investor.contact.name} — {self.get_movement_type_display()} {self.amount:,}"

    @property
    def signed_amount(self):
        return self.amount if self.movement_type == self.MovementType.DEPOSIT else -self.amount


class ExpenseChargePayment(AuditableModel, TimeStampedModel):
    """لینک هر پرداخت (کامل/قسطی) به هزینه ماهانه."""

    charge = models.ForeignKey(ExpenseCharge, on_delete=models.CASCADE,
                               related_name="installments", verbose_name="هزینه")
    payment = models.OneToOneField("accounting.Payment", on_delete=models.PROTECT,
                                   related_name="expense_installment", verbose_name="سند پرداخت")
    amount = models.BigIntegerField(verbose_name="مبلغ (ریال)")

    class Meta:
        db_table = "expense_charge_payment"
        verbose_name = "پرداخت هزینه"
        verbose_name_plural = "پرداخت‌های هزینه"

    def __str__(self):
        return f"پرداخت {self.amount:,} ریال — {self.charge}"
