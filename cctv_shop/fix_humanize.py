import os

# اضافه کردن humanize به settings
settings_path = os.path.join('config', 'settings.py')
with open(settings_path, encoding='utf-8') as f:
    settings = f.read()

if 'django.contrib.humanize' not in settings:
    settings = settings.replace(
        '"apps.accounting"',
        '"apps.accounting",\n    "django.contrib.humanize"'
    )
    with open(settings_path, 'w', encoding='utf-8') as f:
        f.write(settings)
    print("✓ humanize اضافه شد")
else:
    print("✓ قبلاً موجود بود")

# اصلاح template - حذف humanize و استفاده از فیلتر ساده
template_path = os.path.join('templates', 'admin', 'accounting', 'balance_report.html')
with open(template_path, encoding='utf-8') as f:
    content = f.read()

# جایگزینی intcomma با فیلتر ساده
content = content.replace('{% load humanize %}', '')
content = content.replace('|intcomma', '')
content = content.replace('|floatformat:0|intcomma', '|floatformat:0')

with open(template_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ template اصلاح شد")
print("سرور را restart کنید")
