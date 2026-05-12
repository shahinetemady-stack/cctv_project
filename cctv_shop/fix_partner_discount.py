"""
python fix_partner_discount.py
تخفیف همکار روی پروفایل کاربر
"""
import os, subprocess, sys

print("اضافه کردن تخفیف همکار به پروفایل کاربر ...")

# ─── 1. migration برای UserProfile ───────────────────────
migration = '''from django.db import migrations, models
from decimal import Decimal
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="discount_percent",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, default=Decimal("0"),
                verbose_name="درصد تخفیف همکار",
                help_text="مثال: 15 یعنی ۱۵٪ تخفیف روی قیمت نهایی",
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0")),
                    django.core.validators.MaxValueValidator(Decimal("100")),
                ],
            ),
        ),
    ]
'''

mig_path = os.path.join('apps','users','migrations','0002_partner_discount.py')
os.makedirs(os.path.dirname(mig_path), exist_ok=True)
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration users")

# ─── 2. برگرداندن migration catalog به حالت ساده ─────────
# حذف partner_discount_percent از ProductVariant
cat_migration = '''from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_fix_pricing_fields"),
    ]
    operations = []
'''
# اگر migration 0008 از قبل هست آن را بازنویسی کن
mig8 = os.path.join('apps','catalog','migrations','0008_partner_price.py')
if os.path.exists(mig8):
    with open(mig8, 'w', encoding='utf-8') as f:
        f.write(cat_migration)
    print("  OK - migration catalog 0008 خالی شد")

# ─── 3. UserProfile model: اضافه کردن discount_percent ──
users_path = os.path.join('apps','users','models.py')
with open(users_path, encoding='utf-8') as f:
    content = f.read()

old = '''    credit_limit = models.PositiveBigIntegerField(default=0, verbose_name="سقف اعتبار (تومان)")'''
new = '''    credit_limit = models.PositiveBigIntegerField(default=0, verbose_name="سقف اعتبار (تومان)")
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="درصد تخفیف همکار",
        help_text="مثال: 15 یعنی ۱۵٪ تخفیف روی قیمت نهایی",
    )'''

content = content.replace(old, new)
with open(users_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - users/models.py")

# ─── 4. UserSerializer: اضافه کردن discount_percent ─────
ser_path = os.path.join('apps','users','serializers.py')
if os.path.exists(ser_path):
    with open(ser_path, encoding='utf-8') as f:
        content = f.read()
    if 'discount_percent' not in content:
        content = content.replace(
            '"is_approved"',
            '"is_approved", "discount_percent"'
        )
        with open(ser_path, 'w', encoding='utf-8') as f:
            f.write(content)
    print("  OK - users/serializers.py")

# ─── 5. users/admin.py: اضافه کردن فیلد ─────────────────
admin_path = os.path.join('apps','users','admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '"user_type", "company_name", "national_id", "is_approved", "credit_limit", "address", "notes"',
    '"user_type", "company_name", "national_id", "is_approved", "discount_percent", "credit_limit", "address", "notes"'
)
with open(admin_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - users/admin.py")

# ─── 6. catalog/serializers.py: اصلاح ProductVariant ────
cat_ser = os.path.join('apps','catalog','serializers.py')
with open(cat_ser, encoding='utf-8') as f:
    content = f.read()

# حذف partner_price از serializer اگر هست
content = content.replace('    partner_price   = serializers.IntegerField(read_only=True)\n', '')
content = content.replace('"partner_price", ', '')
content = content.replace(', "partner_price"', '')
content = content.replace('"partner_discount_percent", ', '')
content = content.replace(', "partner_discount_percent"', '')
with open(cat_ser, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - catalog/serializers.py")

# ─── 7. catalog/models.py: حذف partner_discount_percent ─
cat_models = os.path.join('apps','catalog','models.py')
with open(cat_models, encoding='utf-8') as f:
    content = f.read()

# حذف partner_discount_percent از ProductVariant
old2 = '''    partner_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="تخفیف همکار (%)",
        help_text="درصد تخفیف برای مشتریان همکار. مثال: 15 یعنی ۱۵٪ تخفیف",
    )
    is_active     = models.BooleanField(default=True, verbose_name="فعال")'''
new2 = '''    is_active     = models.BooleanField(default=True, verbose_name="فعال")'''
content = content.replace(old2, new2)

# حذف partner_price property
old3 = '''    @property
    def partner_price(self):
        """قیمت مشتری همکار — با تخفیف روی قیمت نهایی"""
        import math
        base = self.final_price
        discount = base * float(self.partner_discount_percent) / 100
        return math.ceil(base - discount)

    @property
    def is_in_stock(self):'''
new3 = '''    @property
    def is_in_stock(self):'''
content = content.replace(old3, new3)

with open(cat_models, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - catalog/models.py")

# ─── 8. views.py: اضافه کردن partner_price به API ───────
# در ProductDetailView باید قیمت همکار محاسبه و برگردانده شود
cat_views = os.path.join('apps','catalog','views.py')
with open(cat_views, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن partner_price به response
old_detail = '''    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"'''

new_detail = '''    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def retrieve(self, request, *args, **kwargs):
        import math
        response = super().retrieve(request, *args, **kwargs)
        # اضافه کردن قیمت همکار اگر کاربر لاگین کرده
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            discount = float(request.user.profile.discount_percent or 0)
            if discount > 0:
                for v in response.data.get('variants', []):
                    base = v.get('final_price', 0)
                    v['partner_price'] = math.ceil(base * (1 - discount/100))
                    v['partner_discount_percent'] = discount
        return response'''

content = content.replace(old_detail, new_detail)
with open(cat_views, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - catalog/views.py")

# ─── 9. migrate ──────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-6:]:
        if line.strip(): print(" ", line)

r2 = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                    capture_output=True, text=True)
print("  OK - check موفق" if r2.returncode == 0 else "  خطا در check")

print("\nتمام! حالا بزنید: python manage.py runserver")
