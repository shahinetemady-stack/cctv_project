import os, subprocess, sys

print("اصلاح فرمول قیمت‌گذاری ...")

# ─── 1. migration: تغییر shipping_cost از تومان به یوان + profit_percent ──
migration = '''from django.db import migrations, models
import django.core.validators
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_add_field_choices"),
    ]
    operations = [
        # هزینه حمل: از تومان به یوان
        migrations.RenameField("productvariant", "shipping_cost", "shipping_cost_cny"),
        migrations.AlterField(
            model_name="productvariant",
            name="shipping_cost_cny",
            field=models.DecimalField(
                max_digits=8, decimal_places=2, default=0,
                verbose_name="هزینه حمل (یوان)",
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        # سود: از تومان به درصد
        migrations.RenameField("productvariant", "profit_margin", "profit_percent"),
        migrations.AlterField(
            model_name="productvariant",
            name="profit_percent",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, default=0,
                verbose_name="سود (%)",
                help_text="درصد سود روی قیمت خرید + حمل. مثال: 20 یعنی ۲۰٪",
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
    ]
'''

mig_path = os.path.join('apps','catalog','migrations','0007_fix_pricing_fields.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration ساخته شد")

# ─── 2. بروزرسانی models.py: فرمول جدید ──────────────────────────────────
models_path = os.path.join('apps','catalog','models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

# تغییر فیلدها در ProductVariant
old_fields = '''    purchase_price_cny = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="قیمت خرید (یوان)",
    )
    shipping_cost = models.PositiveBigIntegerField(default=0, verbose_name="هزینه حمل (تومان)")
    profit_margin = models.PositiveBigIntegerField(default=0, verbose_name="سود (تومان)")'''

new_fields = '''    purchase_price_cny = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="قیمت خرید (یوان)",
        help_text="قیمت خرید به یوان چینی",
    )
    shipping_cost_cny = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="هزینه حمل (یوان)",
        help_text="هزینه حمل به یوان چینی",
    )
    profit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="سود (%)",
        help_text="درصد سود روی قیمت خرید + حمل. مثال: 20 یعنی ۲۰٪",
    )'''

content = content.replace(old_fields, new_fields)

# تغییر فرمول final_price
old_price = '''    @property
    def final_price(self):
        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt
        return int(self.purchase_price_cny * rate) + self.shipping_cost + self.profit_margin'''

new_price = '''    @property
    def final_price(self):
        import math
        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt
        # قیمت خرید به تومان
        purchase_toman  = self.purchase_price_cny * rate
        # هزینه حمل به تومان
        shipping_toman  = self.shipping_cost_cny * rate
        # مجموع قبل از سود
        subtotal        = purchase_toman + shipping_toman
        # سود
        profit_toman    = subtotal * (self.profit_percent / 100)
        # قیمت نهایی - رند به سمت بالا
        return math.ceil(float(subtotal + profit_toman))'''

content = content.replace(old_price, new_price)

with open(models_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - models.py بروزرسانی شد")

# ─── 3. بروزرسانی admin.py: فیلدهای جدید ──────────────────────────────────
admin_path = os.path.join('apps','catalog','admin.py')
with open(admin_path, encoding='utf-8') as f:
    a = f.read()

a = a.replace(
    '"sku", "purchase_price_cny", "shipping_cost", "profit_margin", "stock_quantity", "is_active"',
    '"sku", "purchase_price_cny", "shipping_cost_cny", "profit_percent", "stock_quantity", "is_active"'
)
a = a.replace(
    '"sku", "product", "purchase_price_cny", "stock_quantity", "is_active"',
    '"sku", "product", "purchase_price_cny", "shipping_cost_cny", "profit_percent", "stock_quantity", "is_active"'
)
with open(admin_path, 'w', encoding='utf-8') as f:
    f.write(a)
print("  OK - admin.py بروزرسانی شد")

# ─── 4. migrate ────────────────────────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-6:]:
        if line.strip(): print(" ", line)
    sys.exit(1)

r2 = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                    capture_output=True, text=True)
if r2.returncode == 0:
    print("  OK - همه چیز درست است!")
else:
    for line in (r2.stdout+r2.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)

print("\nتمام! حالا بزنید: python manage.py runserver")
