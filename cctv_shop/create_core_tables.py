import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # بررسی جداول موجود
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'core_%'")
    tables = cursor.fetchall()
    print("Core tables:", tables)

    # ساخت core_site_settings اگر نبود
    if not any('core_site_settings' in t[0] for t in tables):
        cursor.execute("""
            CREATE TABLE core_site_settings (
                id INTEGER PRIMARY KEY,
                site_name VARCHAR(100) DEFAULT 'فروشگاه قطعات دوربین',
                site_logo VARCHAR(100),
                contact_phone VARCHAR(20) DEFAULT '',
                contact_email VARCHAR(254) DEFAULT '',
                contact_address TEXT DEFAULT '',
                working_hours VARCHAR(200) DEFAULT 'شنبه تا پنج‌شنبه ۹-۱۸',
                whatsapp_number VARCHAR(20) DEFAULT '',
                bale_username VARCHAR(50) DEFAULT '',
                eitaa_username VARCHAR(50) DEFAULT '',
                telegram_username VARCHAR(50) DEFAULT '',
                instagram_username VARCHAR(50) DEFAULT '',
                about_us_text TEXT DEFAULT '',
                bank_accounts TEXT DEFAULT '[]'
            )
        """)
        cursor.execute("INSERT INTO core_site_settings (id, site_name) VALUES (1, 'فروشگاه قطعات دوربین')")
        print("✓ core_site_settings ساخته شد")

    # ساخت core_static_page اگر نبود
    if not any('core_static_page' in t[0] for t in tables):
        cursor.execute("""
            CREATE TABLE core_static_page (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)
        from django.utils import timezone
        now = timezone.now().isoformat()
        cursor.execute("""
            INSERT INTO core_static_page (key, title, content, updated_at) VALUES
            ('terms', 'قوانین و مقررات', '<h2>۱. شرایط استفاده</h2><p>با استفاده از این سایت، شما با تمام قوانین و مقررات آن موافقت می‌کنید.</p><h2>۲. سفارش و پرداخت</h2><p>تمام سفارشات پس از تأیید موجودی کالا و دریافت پرداخت پردازش می‌شوند.</p><h2>۳. ضمانت</h2><p>کالاهای معیوب تا ۷ روز پس از دریافت قابل مرجوع هستند.</p>', ?),
            ('privacy', 'حریم خصوصی', '<h2>۱. اطلاعات جمع‌آوری شده</h2><p>اطلاعات شما برای پردازش سفارشات استفاده می‌شود و به اشخاص ثالث فروخته نمی‌شود.</p><h2>۲. امنیت</h2><p>تمام اطلاعات با پروتکل‌های امنیتی استاندارد محافظت می‌شود.</p>', ?)
        """, [now, now])
        print("✓ core_static_page ساخته شد")

# fake migrate
import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'migrate', 'core', '--fake'],
                   capture_output=True, text=True)
print(r.stdout[-100:] if r.stdout else "")

r2 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ ok" if r2.returncode == 0 else r2.stderr[-200:])
print("restart server")
