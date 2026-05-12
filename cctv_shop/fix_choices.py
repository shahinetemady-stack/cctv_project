"""
python fix_choices.py
فیلدهای محصول را به dropdown تبدیل می‌کند
"""
import os, subprocess, sys

print("تبدیل فیلدها به dropdown...")

# ─── migration جدید ──────────────────────────────────────────────────────────
migration = '''from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_remove_extra_specs"),
    ]
    operations = [
        # ── لنز: فیلدها با choices ──────────────────────────────────────────
        migrations.AlterField("product", "lens_type",
            models.CharField(max_length=50, blank=True, verbose_name="نوع لنز",
                choices=[
                    ("فیکس","فیکس"),("وریفکال","وریفکال"),
                    ("فیش آی","فیش آی"),("پین هولد","پین هولد"),
                    ("موتورایز","موتورایز"),
                ])),
        migrations.AlterField("product", "lens_degree",
            models.CharField(max_length=20, blank=True, verbose_name="فاصله کانونی",
                choices=[
                    ("1.7mm","1.7mm"),("1.8mm","1.8mm"),("2.8mm","2.8mm"),
                    ("3.6mm","3.6mm"),("4mm","4mm"),("6mm","6mm"),
                    ("8mm","8mm"),("12mm","12mm"),("16mm","16mm"),
                ])),
        migrations.AlterField("product", "lens_resolution",
            models.CharField(max_length=20, blank=True, verbose_name="رزولوشن لنز",
                choices=[("3MP","3MP"),("5MP","5MP"),("8MP","8MP")])),
        migrations.AlterField("product", "focal_ratio",
            models.CharField(max_length=30, blank=True, verbose_name="نوع کاربرد",
                choices=[
                    ("معمولی","معمولی"),("استارلایت","استارلایت"),("دارک لایت","دارک لایت"),
                ])),

        # ── برد: سیستم با choices ───────────────────────────────────────────
        migrations.AlterField("product", "board_system",
            models.CharField(max_length=20, blank=True, verbose_name="سیستم",
                choices=[("AHD","AHD"),("IP","IP")])),
        migrations.AlterField("product", "board_resolution",
            models.CharField(max_length=20, blank=True, verbose_name="رزولوشن (برد)",
                choices=[
                    ("2MP","2MP"),("4MP","4MP"),("5MP","5MP"),
                    ("8MP","8MP"),("12MP","12MP"),
                ])),
        migrations.AlterField("product", "sensor_size",
            models.CharField(max_length=30, blank=True, verbose_name="اندازه سنسور",
                choices=[
                    ('1/4"','1/4"'),('1/3"','1/3"'),('1/2.8"','1/2.8"'),
                    ('1/2.7"','1/2.7"'),('1/2"','1/2"'),('1/1.8"','1/1.8"'),
                ])),

        # ── بدنه: جنس با choices ─────────────────────────────────────────────
        migrations.AlterField("product", "housing_material",
            models.CharField(max_length=50, blank=True, verbose_name="جنس بدنه",
                choices=[
                    ("فلز","فلز"),("پلاستیک","پلاستیک"),("فلز و پلاستیک","فلز و پلاستیک"),
                ])),
        migrations.AlterField("product", "housing_type",
            models.CharField(max_length=50, blank=True, verbose_name="نوع بدنه",
                choices=[
                    ("Bullet","Bullet"),("Dome","Dome"),("Box","Box"),
                    ("PTZ","PTZ"),("Fisheye","Fisheye"),
                ])),
    ]
'''

path = os.path.join('apps','catalog','migrations','0006_add_field_choices.py')
with open(path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration ساخته شد")

# migrate
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)
    sys.exit(1)

print("\nتمام! حالا بزنید: python manage.py runserver")
