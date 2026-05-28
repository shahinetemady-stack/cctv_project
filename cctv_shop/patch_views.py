import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن محل SaleItem.objects.create
idx = content.find('SaleItem.objects.create')
if idx < 0:
    print("ERROR: SaleItem.objects.create not found")
    exit()

# نمایش ۵۰۰ کاراکتر اطراف
print("=== کد فعلی ===")
print(repr(content[idx-50:idx+300]))
print("================")

# پیدا کردن کل بلاک for
for_start = content.rfind('for item_data in d.get', 0, idx)
print(f"\nfor loop at: {for_start}")
print(repr(content[for_start:for_start+400]))
