"""
apps/production/models.py
─────────────────────────
امور تولید: دستوره مونتاژ (BOM) + دستور مونتاژ.
محصول نهایی یک Product معمولی است (دسته «دوربین و دستگاه ضبط») با یک واریانت —
پس بدون هیچ تغییری در سایت/سبد/فاکتور قابل فروش است. اجرای مونتاژ موجودی قطعات
را از انبار کم و محصول نهایی را اضافه می‌کند و بهای تمام‌شده را در
purchase_price_cny واریانت نهایی (تقسیم بر نرخ یوان روز) می‌نشاند تا
قیمت‌های سایت از همان فرمول دسته محاسبه شوند.
"""
from django.conf import settings
from django.db import models


class AssemblyRecipe(models.Model):
    """دستوره مونتاژ (BOM) یک محصول نهایی — هر محصول نهایی یک رسیپی دارد."""
    product    = models.OneToOneField("catalog.Product", on_delete=models.CASCADE,
                    related_name="assembly_recipe", verbose_name="محصول نهایی")
    note       = models.TextField(blank=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "production_assembly_recipe"
        verbose_name = "دستوره مونتاژ"
        verbose_name_plural = "دستوره‌های مونتاژ"

    def __str__(self):
        return f"رسیپی {self.product.name}"


class AssemblyRecipeItem(models.Model):
    """یک قطعه در دستوره مونتاژ — به ازای هر یک دستگاه خروجی."""
    recipe    = models.ForeignKey(AssemblyRecipe, on_delete=models.CASCADE,
                  related_name="items", verbose_name="دستوره")
    component = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT,
                  related_name="assembly_usages", verbose_name="قطعه")
    quantity  = models.PositiveIntegerField(default=1, verbose_name="تعداد در هر دستگاه")

    class Meta:
        db_table = "production_assembly_recipe_item"
        verbose_name = "قطعه دستوره مونتاژ"
        verbose_name_plural = "قطعات دستوره مونتاژ"
        unique_together = [("recipe", "component")]

    def __str__(self):
        return f"{self.component} × {self.quantity}"


class AssemblyOrder(models.Model):
    """دستور مونتاژ — هر اجرا: مصرف قطعات + تولید محصول نهایی در یک انبار."""
    class Status(models.TextChoices):
        DONE      = "done",      "انجام شده"
        CANCELLED = "cancelled", "برگشت داده شده"

    product        = models.ForeignKey("catalog.Product", on_delete=models.PROTECT,
                        related_name="assembly_orders", verbose_name="محصول نهایی")
    quantity       = models.PositiveIntegerField(verbose_name="تعداد تولید")
    warehouse      = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT,
                        related_name="assembly_orders", verbose_name="انبار")
    unit_cost_irr  = models.PositiveBigIntegerField(default=0, verbose_name="بهای تمام‌شده واحد (ریال)")
    total_cost_irr = models.PositiveBigIntegerField(default=0, verbose_name="بهای تمام‌شده کل (ریال)")
    # اجرت مونتاژ و لوازم مصرفی — برون‌سپاری به طرف حساب؛ جزو بهای تمام‌شده لحاظ و
    # به‌صورت سند هزینه (ExpenseCharge) در حساب مونتاژکار ثبت می‌شود
    labor_cost_irr       = models.PositiveBigIntegerField(default=0, verbose_name="اجرت مونتاژ (ریال)")
    consumables_cost_irr = models.PositiveBigIntegerField(default=0, verbose_name="لوازم مصرفی (ریال)")
    assembler      = models.ForeignKey("accounting.Contact", on_delete=models.PROTECT,
                        null=True, blank=True, related_name="assembly_orders",
                        verbose_name="مونتاژکار (طرف حساب)")
    expense_charge = models.ForeignKey("expenses.ExpenseCharge", on_delete=models.SET_NULL,
                        null=True, blank=True, related_name="assembly_orders",
                        verbose_name="سند هزینه")
    status         = models.CharField(max_length=20, choices=Status.choices,
                        default=Status.DONE, verbose_name="وضعیت")
    note           = models.TextField(blank=True, verbose_name="توضیحات")
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                        null=True, blank=True, verbose_name="ثبت‌کننده")
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "production_assembly_order"
        verbose_name = "دستور مونتاژ"
        verbose_name_plural = "دستورهای مونتاژ"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} × {self.quantity} ({self.get_status_display()})"
