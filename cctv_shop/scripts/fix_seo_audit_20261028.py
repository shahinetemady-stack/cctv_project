# اصلاحات ممیزی سئو/املای 2026-10-28 — امن برای اجرای مجدد (idempotent)
# اجرا: ./venv/bin/python scripts/fix_seo_audit_20261028.py
import os
import re
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.catalog.models import Category, Product
from apps.education.models import Article

Z = "\u200c"

# ۱) نیم‌فاصله پسوندهای لاتین (LEDهای → LED‌ها و…) در توضیحات محصولات و دسته‌ها
LATIN_SUFFIX = [
    ("LEDهای", f"LED{Z}ها"), ("LEDها", f"LED{Z}ها"),
    ("CUTهای", f"CUT{Z}ها"), ("NVRهای", f"NVR{Z}ها"),
]
n = 0
for p in Product.objects.all():
    d = p.description or ""
    nd = d
    for a, b in LATIN_SUFFIX:
        nd = nd.replace(a, b)
    nd = re.sub(r" {2,}", " ", nd)
    if nd != d:
        p.description = nd
        p.save(update_fields=["description"])
        n += 1
for c in Category.objects.all():
    d = c.description or ""
    nd = d
    for a, b in LATIN_SUFFIX:
        nd = nd.replace(a, b)
    if nd != d:
        c.description = nd
        c.save(update_fields=["description"])
        n += 1
print("spell fixed:", n)

# ۲) فاصله دوبل در عنوان مقاله ۱۱
a = Article.objects.filter(id=11).first()
if a and "  " in a.title:
    a.title = " ".join(a.title.split())
    a.save(update_fields=["title"])
    print("A11 fixed")

# ۳) متای دسته‌های دوربین/دستگاه مونتاژی
CATS = {
    27: ("دوربین مداربسته و دستگاه ضبط مونتاژی | دوربینکار",
         "دوربین‌های مونتاژی AHD و IP با برد، لنز و بدنه منتخب مونتاژکاران دوربینکار؛ دوربین بولت و دام فلزی وارم‌لایت آماده نصب با قیمت همکار و ارسال به سراسر ایران."),
    28: ("دوربین مداربسته مونتاژی بولت و دام | قیمت و خرید",
         "خرید دوربین مداربسته مونتاژی (بولت و دام فلزی) با سنسور و برد اورجینال؛ تصویر ۲ تا ۸ مگاپیکسل، وارم‌لایت فول‌کالر، دید در شب رنگی. قیمت همکار و ارسال سریع از دوربینکار."),
    29: ("دستگاه ضبط DVR و NVR مونتاژی | قیمت و خرید",
         "دستگاه‌های ضبط DVR و NVR مونتاژی ۴ تا ۱۶ کانال با بردهای RUISION؛ پشتیبانی هارد، خروجی HDMI تا 4K و اپلیکیشن HiEasy. قیمت همکار و ارسال به سراسر کشور."),
}
for cid, (t, d) in CATS.items():
    c = Category.objects.filter(id=cid).first()
    if not c:
        continue
    changed = []
    if not c.meta_title:
        c.meta_title = t
        changed.append("meta_title")
    if not c.meta_description:
        c.meta_description = d
        changed.append("meta_description")
    if changed:
        c.save(update_fields=changed)
    print("CAT", cid, "set:", changed)

# ۴) تکمیل محصول بدنه DVR فلزی (۴ کانال RUISION)
p = Product.objects.filter(id=144).first()
if p:
    p.brand = "RUISION"
    p.slug = "ruision-dvr-housing-4ch-metal"  # اسلاگ قدیمی با 301 خودکار ثبت می‌شود
    p.short_description = ("بدنه فلزی دستگاه DVR چهارکانال RUISION با جای یک هارد و نصب رومیزی؛ "
                           "مناسب مونتاژ و تعمیر دستگاه ضبط.")
    p.description = (
        "بدنه فلزی دستگاه DVR چهارکانال RUISION برای مونتاژ و تعمیر دستگاه‌های ضبط چهارکاناله "
        "عرضه می‌شود؛ فضای نصب یک هارد دیسک، بدنه فلزی مقاوم رنگ طوسی و طراحی رومیزی که روی "
        "میز یا داخل رک کوچک جای می‌گیرد.\n\n"
        "این بدنه با بردهای DVR چهارکانال سازگار است و بدون پاور داخلی عرضه می‌شود تا مونتاژکار "
        "آداپتور متناسب را جداگانه انتخاب کند. ارسال به تهران، کرج و سراسر کشور از فروشگاه دوربینکار."
    )
    p.meta_description = ("بدنه فلزی دستگاه DVR چهارکانال RUISION؛ جای ۱ هارد، نصب رومیزی، "
                          "مناسب مونتاژ و تعمیر دی‌وی‌آر. قیمت همکار و ارسال سریع از دوربینکار.")
    p.keywords = ("کیس DVR، بدنه دستگاه دی وی آر، بدنه DVR فلزی، کیس دستگاه ضبط، بدنه DVR روویژن، "
                  "RUISION، قاب دستگاه ضبط دوربین، بدنه دی وی آر ۴ کانال، مونتاژ DVR، قیمت کیس DVR")
    p.geo_tags = "تهران، کرج، مشهد، اصفهان، شیراز، تبریز، قم، اهواز، رشت، کرمان"
    p.save()
    print("P144 completed:", p.slug)
