import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounting.models import Contact
cs = Contact.objects.filter(is_active=True)
print(f"تعداد contacts: {cs.count()}")
for c in cs:
    try:
        birr = c.balance_irr
        bcny = c.balance_cny
        print(f"OK: {c.name} | IRR={birr} | CNY={bcny}")
    except Exception as e:
        print(f"ERROR: {c.name} | {e}")
