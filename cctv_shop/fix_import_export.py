import os, subprocess, sys

print("حذف import_export از admin ...")

with open(os.path.join('apps','catalog','admin.py'), encoding='utf-8') as f:
    content = f.read()

content = content.replace('from import_export.admin import ImportExportModelAdmin\n', '')
content = content.replace('from import_export import resources\n', '')
content = content.replace('from import_export import resources, fields\n', '')
content = content.replace('(ImportExportModelAdmin)', '(admin.ModelAdmin)')

# حذف resource_class
lines = content.split('\n')
new_lines = []
for line in lines:
    if 'resource_class' in line or 'ProductVariantResource' in line:
        continue
    new_lines.append(line)

# حذف کلاس ProductVariantResource
result = []
skip = False
for line in new_lines:
    if 'class ProductVariantResource' in line:
        skip = True
    elif skip and line.startswith('class ') and 'ProductVariantResource' not in line:
        skip = False
    if not skip:
        result.append(line)

content = '\n'.join(result)

with open(os.path.join('apps','catalog','admin.py'), 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")

# بررسی
import ast
try:
    ast.parse(content)
    print("OK - syntax درست است")
except SyntaxError as e:
    print(f"ERROR: {e}")

r = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("OK - همه چیز درست است!")
    print("حالا بزنید: python manage.py runserver")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)
