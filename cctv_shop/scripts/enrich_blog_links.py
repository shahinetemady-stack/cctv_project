# -*- coding: utf-8 -*-
"""
اجرای یک‌باره روی سرور (بعد از seed_longtail_articles.py):
    cd /opt/cctv/backend && /opt/cctv/venv/bin/python manage.py shell -c "exec(open('/tmp/enrich_blog_links.py', encoding='utf-8').read())"

۱) ادغام مقاله قدیمی dome-vs-bullet-cctv در bullet-vs-dome-housing-guide:
   محتوای مفیدش قبلاً در مقاله جدید ادغام شده؛ اینجا ریدایرکت ۳۰۱ ثبت و مقاله قدیمی حذف می‌شود.
۲) افزودن لینک داخلی (محصول/دسته/مقاله) به ۹ مقاله قبلی + اصلاح چند اشکال ریز HTML اسکریپ‌شده.
idempotent است.
"""

from apps.education.models import Article
from apps.catalog.models import SlugRedirect

# ── ۱) ادغام dome-vs-bullet ─────────────────────────────────────────
old = Article.objects.filter(slug="dome-vs-bullet-cctv").first()
if old:
    SlugRedirect.record("/blog/dome-vs-bullet-cctv", "/blog/bullet-vs-dome-housing-guide")
    old.delete()
    print("✓ dome-vs-bullet-cctv حذف و 301 ثبت شد")
else:
    print("= dome-vs-bullet-cctv قبلاً حذف شده")

# ── ۲) اصلاحات متنی (replace دقیق) ─────────────────────────────────
FIXES = {
    "800g-camera-board-review": [
        (
            "<p>متعادل و قابل‌استفاده ثبت شود. این ویژگی برای مکان‌هایی مانند ورودی ساختمان‌ها، پارکینگ‌ها و خیابان‌های پرتردد بسیار کاربردی است.</p>",
            "<p>رنج دینامیکی بالا (HDR) باعث می‌شود جزئیات در تاریک‌ترین و روشن‌ترین نقاط صحنه به‌صورت هم‌زمان متعادل و قابل‌استفاده ثبت شود. این ویژگی برای مکان‌هایی مانند ورودی ساختمان‌ها، پارکینگ‌ها و خیابان‌های پرتردد بسیار کاربردی است.</p>",
        ),
    ],
    "cctv-board-and-image-sensor-selection-guide": [
        ("</ul>\n<p>IMX415</p>", "<li>\n<p>IMX415</p>\n</li>\n</ul>"),
        ("</ul>\n<p>GC4653</p>", "<li>\n<p>GC4653</p>\n</li>\n</ul>"),
        ("</ul>\n<p>پروژه‌های سفارشی</p>", "<li>\n<p>پروژه‌های سفارشی</p>\n</li>\n</ul>"),
        ("<p>تست پایداری 24 ساعته</p>", "<ul><li><p>تست پایداری 24 ساعته</p></li></ul>"),
        ("</ul>\n<p>داشته باشد</p>", "</ul>\n<p>را داشته باشد.</p>"),
    ],
}

# ── ۳) پاراگراف لینک‌دهی انتهای هر مقاله ───────────────────────────
APPENDS = {
    "what-is-ir-cut": "<p>اگر برای مونتاژ یا تعمیر به لنز با آی‌آر کات یکپارچه نیاز دارید، <a href=\"/products/لنز-و-آی-آر-کات-وریفکال-5-مگاپیکسل-27-135/\">لنز و آی‌آر کات وریفکال ۵ مگاپیکسل ۲.۷ تا ۱۳.۵</a> را ببینید. و اگر تصویر شب دوربین‌تان سفید یا تار شده، علت را در مقاله <a href=\"/blog/night-vision-white-blurry-image/\">چرا تصویر شب دوربین سفید یا تار می‌شود؟</a> پیدا کنید؛ در بیشتر موارد مشکل از همین ناحیه است.</p>",
    "color-night-vision-cctv-cameras": "<p>برای ارتقای دید در شب، چند گزینه آماده در فروشگاه موجود است: <a href=\"/products/لنز-و-هولدر-استارلایت-5-مگاپیکسل-yt-10081b-5mpholder/\">لنز استارلایت پنج‌مگاپیکسل</a> برای سنسورهای حساس به نور، <a href=\"/products/ruision-h4sp-blacklight-ip-board/\">برد بلک‌لایت H4SP</a> برای تصویر رنگی در نور بسیار کم، و انواع <a href=\"/categories/cctv-led/\">LED مادون‌قرمز و وارم‌لایت</a> برای تعویض یا ارتقا. اگر می‌خواهید کیس آماده با وارم‌لایت مونتاژ کنید، <a href=\"/products/کیس-دام-فلزی-دوربین-مداربسته-n665m-warm/\">کیس دام فلزی N665M-WARM</a> را هم ببینید.</p>",
    "cloud-storage-for-cctv": "<p>اگر هزینه اشتراک ابری برای پروژه‌تان توجیه ندارد، ذخیره‌سازی محلی هنوز راه‌حل اصلی بازار است: برای دوربین‌های مستقل، <a href=\"/products/k2-k4b-tf-card-micro-sd-board/\">برد رم و رله TF K2/K4B</a> ضبط روی میکروSD را بدون دستگاه ضبط ممکن می‌کند و بردهای <a href=\"/categories/ip-camera-board/\">دسته IP</a> هم مستقیم به NVR وصل می‌شوند. در پروژه‌هایی که اینترنت ثابت ندارند، ترکیب ضبط محلی با یک <a href=\"/categories/modem-cctv/\">مودم 4G</a> برای انتقال تصویر، معمولاً جواب‌گوتر از فضای ابری است.</p>",
    "ai-cctv-camera-2025": "<p>این قابلیت‌ها روی کاغذ نمانده‌اند؛ <a href=\"/products/t5ai-f-smart-ai-ip-camera-board/\">برد پلاک‌خوان T5AI</a> خواندن پلاک و <a href=\"/products/برد-دوربین-ip-پنج-مگاپیکسل-h4/\">برد H4</a> تشخیص انسان و خودرو را به‌صورت آماده ارائه می‌دهند — برای مونتاژکار یعنی ساخت دوربین AI بدون یک خط توسعه نرم‌افزار. مدل‌های بیشتر را در دسته <a href=\"/categories/ip-camera-board/\">برد دوربین IP</a> ببینید.</p>",
    "800g-camera-board-review": "<p>اگر می‌خواهید این کلاس سنسور را با گزینه‌های رایج بازار ایران مقایسه کنید، <a href=\"/blog/cctv-board-and-image-sensor-selection-guide/\">راهنمای انتخاب برد و سنسور</a> را بخوانید؛ بردهای آماده هم در دسته <a href=\"/categories/ip-camera-board/\">برد دوربین IP</a> قابل مقایسه‌اند.</p>",
    "common-cctv-assembly-issues-and-solutions": "<p>بیشتر قطعاتی که در این مقاله نام بردیم — از <a href=\"/categories/fixed-lens/\">لنز ثابت استاندارد</a> و <a href=\"/categories/cctv-led/\">LED مادون‌قرمز</a> تا <a href=\"/categories/ip-camera-board/\">بردهای IP</a> و <a href=\"/categories/camera-device-housing/\">کیس‌های فلزی با تهویه مناسب</a> — در فروشگاه موجود است. اگر با مشکل تصویر شب دست‌وپنجه نرم می‌کنید، مقاله <a href=\"/blog/night-vision-white-blurry-image/\">چرا تصویر شب سفید یا تار می‌شود؟</a> را هم بخوانید.</p>",
    "cctv-board-and-image-sensor-selection-guide": "<p>چند مطلب تکمیلی و چند محصول آماده برای شروع: تفاوت پردازشگر فولهان و سنسور سونی را در مقاله <a href=\"/blog/fullhan-vs-sony-cctv-board/\">تفاوت برد فولهان و سونی</a> بخوانید و برای انتخاب فاصله کانونی، <a href=\"/blog/cctv-lens-focal-length-guide/\">راهنمای انتخاب لنز</a> را ببینید. از بردهای آماده فروشگاه، <a href=\"/products/برد-دوربین-ahd-دومگاپیکسل-v201/\">برد AHD دومگاپیکسل V201</a> و <a href=\"/products/برد-دوربین-ip-پنج-مگاپیکسل-h4/\">برد IP پنج‌مگاپیکسل H4</a> نقطه شروع خوبی‌اند و <a href=\"/categories/fixed-lens/\">لنزهای ثابت</a> هم در دسته خودشان موجود است.</p>",
    "shenzhen-ruision-technology-company-introduction": "<p>محصولات Ruision در فروشگاه هم موجود است: <a href=\"/products/برد-دوربین-ip-پنج-مگاپیکسل-h4/\">برد H4 پنج‌مگاپیکسل</a> و <a href=\"/products/ruision-h4sp-blacklight-ip-board/\">برد بلک‌لایت H4SP</a> ساخت همین شرکت‌اند و در دسته <a href=\"/categories/ip-camera-board/\">برد دوربین IP</a> با قیمت همکار عرضه می‌شوند.</p>",
    "shenzhen-vatilon-electronics-company-introduction": "<p>برای دیدن گزینه‌های مشابه در بازار ایران، دسته‌های <a href=\"/categories/ip-camera-board/\">برد دوربین IP</a> و <a href=\"/categories/ahd-camera-board/\">برد دوربین AHD</a> را ببینید؛ و اگر بین این دو فناوری مردد هستید، مقاله <a href=\"/blog/ahd-vs-ip-existing-cabling/\">AHD یا IP؟ انتخاب بر اساس کابل‌کشی موجود</a> را بخوانید.</p>",
}

for slug, fixes in FIXES.items():
    a = Article.objects.get(slug=slug)
    changed = False
    for old_s, new_s in fixes:
        if old_s in a.content:
            a.content = a.content.replace(old_s, new_s, 1)
            changed = True
        elif new_s in a.content:
            pass  # قبلاً اصلاح شده
        else:
            print(f"⚠ الگو پیدا نشد در {slug}: {old_s[:50]!r}")
    if changed:
        a.save(update_fields=["content"])
        print("✓ اصلاح متنی:", slug)

for slug, addition in APPENDS.items():
    a = Article.objects.get(slug=slug)
    marker = addition[:60]
    if marker in a.content:
        print("= لینک قبلاً اضافه شده:", slug)
        continue
    a.content = a.content.rstrip() + addition
    a.save(update_fields=["content"])
    print("✓ لینک اضافه شد:", slug)

print("مقالات منتشرشده فعلی:", Article.objects.filter(is_published=True).count())
