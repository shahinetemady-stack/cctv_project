"""
apps/inventory/models.py
─────────────────────────
Inventory management models:

  StockMovement  — تاریخچه کامل تمام تغییرات موجودی (audit log)
  StockAlert     — هشدارهای موجودی کم (ارسال ایمیل به ادمین)
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class StockMovement(TimeStampedModel):
    """
    Immutable audit log of every stock change.
    Created automatically by signals or service functions whenever
    stock_quantity or reserved_qty changes.
    """

    class MovementType(models.TextChoices):
        PURCHASE = "purchase", "خرید / دریافت کالا"
        SALE = "sale", "فروش"
        RESERVATION = "reservation", "رزرو"
        RESERVATION_RELEASE = "reservation_release", "آزادسازی رزرو"
        ADJUSTMENT = "adjustment", "تعدیل دستی"
        RETURN = "return", "مرجوعی"
        DAMAGE = "damage", "ضایعات"

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="stock_movements",
        verbose_name="نسخه محصول",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="سفارش مرتبط",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="انجام شده توسط",
    )

    movement_type = models.CharField(
        max_length=25,
        choices=MovementType.choices,
        verbose_name="نوع حرکت موجودی",
    )
    quantity_change = models.IntegerField(
        verbose_name="تغییر تعداد",
        help_text="مثبت = افزایش، منفی = کاهش",
    )
    stock_before = models.PositiveIntegerField(verbose_name="موجودی قبل")
    stock_after = models.PositiveIntegerField(verbose_name="موجودی بعد")
    note = models.CharField(max_length=500, blank=True, verbose_name="یادداشت")

    class Meta:
        db_table = "inventory_stock_movement"
        verbose_name = "حرکت موجودی"
        verbose_name_plural = "حرکات موجودی"
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.quantity_change >= 0 else ""
        return (
            f"{self.get_movement_type_display()} | "
            f"{self.variant.sku}: {sign}{self.quantity_change} "
            f"({self.stock_before} → {self.stock_after})"
        )


class StockAlert(TimeStampedModel):
    """
    Alert record created when a variant's available_stock drops below
    settings.LOW_STOCK_THRESHOLD (default: 5).

    is_resolved is set to True when admin increases stock.
    email_sent tracks whether the admin email has already been sent
    (to avoid duplicate emails).
    """

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="stock_alerts",
        verbose_name="نسخه محصول",
    )
    stock_at_alert = models.PositiveIntegerField(
        verbose_name="موجودی در لحظه هشدار",
    )
    threshold = models.PositiveSmallIntegerField(
        verbose_name="آستانه هشدار",
        help_text="مقدار LOW_STOCK_THRESHOLD در لحظه ایجاد هشدار",
    )
    email_sent = models.BooleanField(
        default=False,
        verbose_name="ایمیل ارسال شد",
    )
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان ارسال ایمیل",
    )
    is_resolved = models.BooleanField(
        default=False,
        verbose_name="برطرف شده",
        db_index=True,
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان برطرف شدن",
    )

    class Meta:
        db_table = "inventory_stock_alert"
        verbose_name = "هشدار موجودی کم"
        verbose_name_plural = "هشدارهای موجودی کم"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["is_resolved", "email_sent"],
                name="idx_alert_unresolved",
            )
        ]

    def __str__(self):
        status = "✓ برطرف" if self.is_resolved else "⚠ فعال"
        return f"هشدار موجودی {self.variant.sku} ({self.stock_at_alert} عدد) — {status}"
