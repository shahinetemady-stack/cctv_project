import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── 1. Footer ───────────────────────────────────────────────
footer_path = os.path.join(FRONTEND, 'components', 'layout', 'Footer.jsx')
with open(footer_path, encoding='utf-8') as f:
    footer = f.read()

# اضافه کردن لینک سفارش از چین به دسترسی سریع
old_links = """              {[
                ['\\u0645\\u062d\\u0635\\u0648\\u0644\\u0627\\u062a', '/products'],
                ['\\u0648\\u0631\\u0648\\u062f', '/auth/login'],
                ['\\u062b\\u0628\\u062a\\u2060\\u0646\\u0627\\u0645 \\u0647\\u0645\\u06a9\\u0627\\u0631', '/auth/register'],
              ]"""

# روش مستقیم‌تر — پیدا کردن آرایه لینک‌ها
import re
# پیدا کردن بخش دسترسی سریع
idx = footer.find("'/products'")
if idx > 0:
    # پیدا کردن پایان آرایه
    arr_start = footer.rfind('[', 0, idx)
    arr_end = footer.find(']', idx) + 1
    old_arr = footer[arr_start:arr_end]
    print("Found array:", repr(old_arr[:100]))

    # اضافه کردن لینک چین
    if 'china-order' not in footer:
        new_arr = old_arr.rstrip(']') + ''',
                ['🇨🇳 سفارش از چین', '/china-order'],
                ['🎁 پکیج‌ها', '/packages'],
              ]'''
        footer = footer[:arr_start] + new_arr + footer[arr_end:]
        print("✓ لینک‌ها اضافه شدند")

with open(footer_path, 'w', encoding='utf-8') as f:
    f.write(footer)
print("✓ Footer آپدیت شد")

# ─── 2. HomePage ─────────────────────────────────────────────
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')
with open(home_path, encoding='utf-8') as f:
    home = f.read()

# اضافه کردن بنر سفارش از چین قبل از footer section
china_banner = """
        {/* بنر سفارش از چین */}
        <section className="relative overflow-hidden rounded-3xl p-8 text-center"
          style={{background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)', border: '1px solid rgba(255,255,255,0.1)'}}>
          <div className="text-4xl mb-3">🇨🇳</div>
          <h3 className="font-display font-bold text-xl text-white mb-2">سفارش مستقیم از چین</h3>
          <p className="text-gray-steel text-sm mb-5 max-w-sm mx-auto">
            کالایی که نمی‌یابید؟ مستقیم از کارخانه‌های چین با بهترین قیمت تهیه می‌کنیم
          </p>
          <Link to="/china-order"
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-brand text-white font-semibold rounded-xl hover:bg-brand/80 transition-colors text-sm">
            ثبت درخواست ←
          </Link>
        </section>

"""

if 'china-order' not in home:
    # اضافه کردن قبل از section همکاران
    old = '        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-l from-brand to-steel'
    if old in home:
        home = home.replace(old, china_banner + '        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-l from-brand to-steel')
        print("✓ بنر چین به HomePage اضافه شد")

# اطمینان از وجود Link import
if 'Link' not in home:
    home = home.replace("import {", "import { Link,")

with open(home_path, 'w', encoding='utf-8') as f:
    f.write(home)
print("✓ HomePage آپدیت شد")
