"""
python fix_partner_price.py
۱. اضافه کردن قیمت همکار به ProductVariant
۲. بروزرسانی serializer برای نمایش قیمت همکار
"""
import os, subprocess, sys

print("اضافه کردن قیمت همکار ...")

# ─── migration ──────────────────────────────────────────
migration = '''from django.db import migrations, models
from decimal import Decimal
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_fix_pricing_fields"),
    ]
    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="partner_discount_percent",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, default=Decimal("0"),
                verbose_name="تخفیف همکار (%)",
                help_text="درصد تخفیف برای مشتریان همکار. مثال: 15 یعنی ۱۵٪ تخفیف",
                validators=[django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("100"))],
            ),
        ),
    ]
'''

mig_path = os.path.join('apps','catalog','migrations','0008_partner_price.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration")

# ─── models.py: اضافه کردن فیلد و property ──────────────
models_path = os.path.join('apps','catalog','models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

old = '''    profit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="سود (%)",
        help_text="درصد سود روی قیمت خرید + حمل. مثال: 20 یعنی ۲۰٪",
    )
    is_active     = models.BooleanField(default=True, verbose_name="فعال")'''

new = '''    profit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="سود (%)",
        help_text="درصد سود روی قیمت خرید + حمل. مثال: 20 یعنی ۲۰٪",
    )
    partner_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="تخفیف همکار (%)",
        help_text="درصد تخفیف برای مشتریان همکار. مثال: 15 یعنی ۱۵٪ تخفیف",
    )
    is_active     = models.BooleanField(default=True, verbose_name="فعال")'''

content = content.replace(old, new)

# اضافه کردن partner_price property
old2 = '''    @property
    def is_in_stock(self):'''

new2 = '''    @property
    def partner_price(self):
        """قیمت مشتری همکار — با تخفیف روی قیمت نهایی"""
        import math
        base = self.final_price
        discount = base * float(self.partner_discount_percent) / 100
        return math.ceil(base - discount)

    @property
    def is_in_stock(self):'''

content = content.replace(old2, new2)

with open(models_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - models.py")

# ─── serializers.py: اضافه کردن partner_price ───────────
ser_path = os.path.join('apps','catalog','serializers.py')
with open(ser_path, encoding='utf-8') as f:
    content = f.read()

old3 = '''class ProductVariantSerializer(serializers.ModelSerializer):
    final_price     = serializers.IntegerField(read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    is_in_stock     = serializers.BooleanField(read_only=True)
    is_low_stock    = serializers.BooleanField(read_only=True)

    class Meta:
        model  = ProductVariant
        fields = ["id", "sku", "name_suffix", "final_price",
                  "available_stock", "is_in_stock", "is_low_stock", "is_active"]'''

new3 = '''class ProductVariantSerializer(serializers.ModelSerializer):
    final_price     = serializers.IntegerField(read_only=True)
    partner_price   = serializers.IntegerField(read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    is_in_stock     = serializers.BooleanField(read_only=True)
    is_low_stock    = serializers.BooleanField(read_only=True)

    class Meta:
        model  = ProductVariant
        fields = ["id", "sku", "name_suffix", "final_price", "partner_price",
                  "partner_discount_percent", "available_stock",
                  "is_in_stock", "is_low_stock", "is_active"]'''

content = content.replace(old3, new3)
with open(ser_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - serializers.py")

# ─── admin.py: اضافه کردن فیلد به inline ───────────────
admin_path = os.path.join('apps','catalog','admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '"sku", "purchase_price_cny", "shipping_cost_cny", "profit_percent", "stock_quantity", "is_active"',
    '"sku", "purchase_price_cny", "shipping_cost_cny", "profit_percent", "partner_discount_percent", "stock_quantity", "is_active"'
)
with open(admin_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - admin.py")

# ─── migrate ─────────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)

print("\nتمام! حالا بزنید: python manage.py runserver")
