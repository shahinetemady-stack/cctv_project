import os, subprocess, sys

print("اصلاح migration 0004 ...")

content = '''"""
Migration 0004 - بازسازی کامل ساختار محصول
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_product_seo_fields"),
    ]
    operations = [
        # ── اول index های قدیمی را حذف کن ────────────────────────
        migrations.RemoveIndex("product", "idx_product_type_chip"),
        migrations.RemoveIndex("product", "idx_product_active_feat"),

        # ── ارز: دلار → یوان ──────────────────────────────────────
        migrations.RenameField("exchangeratesetting", "rate_usd_to_irt", "rate_cny_to_irt"),
        migrations.AlterField(
            model_name="exchangeratesetting",
            name="rate_cny_to_irt",
            field=models.PositiveBigIntegerField(
                default=8500, verbose_name="نرخ یوان (تومان)",
            ),
        ),

        # ── دسته‌بندی: اضافه کردن category_type ──────────────────
        migrations.AddField(
            model_name="category",
            name="category_type",
            field=models.CharField(
                max_length=20, db_index=True, default="other",
                choices=[("board","برد دوربین"),("lens","لنز"),
                         ("modem","متعلقات"),("housing","بدنه"),("other","سایر")],
                verbose_name="نوع دسته",
            ),
        ),

        # ── حذف فیلدهای قدیمی ─────────────────────────────────────
        migrations.RemoveField("product", "part_type"),
        migrations.RemoveField("product", "chipset"),
        migrations.RemoveField("product", "lens_mount"),
        migrations.RemoveField("product", "resolution"),

        # ── ویژگی‌های برد ──────────────────────────────────────────
        migrations.AddField("product","board_name",      models.CharField(max_length=150,blank=True,verbose_name="نام برد")),
        migrations.AddField("product","board_system",    models.CharField(max_length=100,blank=True,verbose_name="سیستم")),
        migrations.AddField("product","board_resolution",models.CharField(max_length=50, blank=True,verbose_name="رزولوشن (برد)")),
        migrations.AddField("product","sensor_name",     models.CharField(max_length=150,blank=True,verbose_name="نام سنسور")),
        migrations.AddField("product","sensor_size",     models.CharField(max_length=50, blank=True,verbose_name="اندازه سنسور")),
        migrations.AddField("product","ai_processor",    models.CharField(max_length=150,blank=True,verbose_name="AI پردازنده")),
        migrations.AddField("product","board_dimensions",models.CharField(max_length=100,blank=True,verbose_name="ابعاد (برد)")),

        # ── ویژگی‌های لنز ──────────────────────────────────────────
        migrations.AddField("product","lens_name",      models.CharField(max_length=150,blank=True,verbose_name="نام لنز")),
        migrations.AddField("product","lens_resolution",models.CharField(max_length=50, blank=True,verbose_name="رزولوشن (لنز)")),
        migrations.AddField("product","lens_degree",    models.CharField(max_length=50, blank=True,verbose_name="درجه لنز")),
        migrations.AddField("product","lens_type",      models.CharField(max_length=100,blank=True,verbose_name="نوع لنز")),
        migrations.AddField("product","focal_ratio",    models.CharField(max_length=50, blank=True,verbose_name="نسبت کانونی")),

        # ── ویژگی‌های متعلقات ──────────────────────────────────────
        migrations.AddField("product","modem_model",  models.CharField(max_length=150,blank=True,verbose_name="مدل")),
        migrations.AddField("product","modem_type",   models.CharField(max_length=100,blank=True,verbose_name="نوع")),
        migrations.AddField("product","pin_count",    models.CharField(max_length=50, blank=True,verbose_name="تعداد پین")),
        migrations.AddField("product","voltage",      models.CharField(max_length=50, blank=True,verbose_name="ولتاژ کاری")),
        migrations.AddField("product","ampere_output",models.CharField(max_length=50, blank=True,verbose_name="آمپر خروجی")),
        migrations.AddField("product","sim_card",     models.BooleanField(default=False,verbose_name="قابلیت سیم کارت")),
        migrations.AddField("product","output_ports", models.PositiveSmallIntegerField(null=True,blank=True,verbose_name="تعداد پورت خروجی")),
        migrations.AddField("product","modem_size",   models.CharField(max_length=100,blank=True,verbose_name="سایز")),

        # ── ویژگی‌های بدنه ─────────────────────────────────────────
        migrations.AddField("product","housing_material",models.CharField(max_length=100,blank=True,verbose_name="جنس بدنه")),
        migrations.AddField("product","housing_type",    models.CharField(max_length=100,blank=True,verbose_name="نوع بدنه")),
        migrations.AddField("product","housing_size",    models.CharField(max_length=100,blank=True,verbose_name="سایز دوربین")),
        migrations.AddField("product","has_microphone",  models.BooleanField(default=False,verbose_name="قابلیت میکروفون")),

        # ── Variant: دلار → یوان ──────────────────────────────────
        migrations.RenameField("productvariant","purchase_price_usd","purchase_price_cny"),
        migrations.AlterField(
            model_name="productvariant",
            name="purchase_price_cny",
            field=models.DecimalField(
                max_digits=10,decimal_places=2,
                verbose_name="قیمت خرید (یوان)",
            ),
        ),
    ]
'''

path = os.path.join('apps','catalog','migrations','0004_restructure_product.py')
with open(path,'w',encoding='utf-8') as f:
    f.write(content)
print("OK - migration اصلاح شد")

r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=1'],
                   capture_output=True, text=True)
lines = (r.stdout+r.stderr).strip().split('\n')
for line in lines:
    if line.strip() and ('OK' in line or 'ERROR' in line or 'Applying' in line or 'Error' in line):
        print(" ", line)

if r.returncode == 0:
    print("\nموفق! حالا بزنید: python manage.py runserver")
else:
    print("\nخطا:")
    for line in lines[-5:]:
        if line.strip(): print(" ", line)
