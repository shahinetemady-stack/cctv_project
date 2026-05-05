import os, subprocess, sys

print("حذف کامل import_export ...")

# 1. از settings.py
with open(os.path.join('config','settings.py'), encoding='utf-8') as f:
    s = f.read()
s = s.replace('    "import_export",\n', '')
with open(os.path.join('config','settings.py'), 'w', encoding='utf-8') as f:
    f.write(s)
print("OK - settings.py")

# 2. از admin.py
with open(os.path.join('apps','catalog','admin.py'), encoding='utf-8') as f:
    a = f.read()
a = a.replace('from import_export.admin import ImportExportModelAdmin\n', '')
a = a.replace('from import_export import resources\n', '')
a = a.replace('from import_export import resources, fields\n', '')
a = a.replace('(ImportExportModelAdmin)', '(admin.ModelAdmin)')
# حذف resource_class
lines = []
for line in a.split('\n'):
    if 'resource_class' not in line and 'ProductVariantResource' not in line:
        lines.append(line)
a = '\n'.join(lines)
with open(os.path.join('apps','catalog','admin.py'), 'w', encoding='utf-8') as f:
    f.write(a)
print("OK - admin.py")

# 3. check
r = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("OK - همه چیز درست است!")
    print("حالا بزنید: python manage.py runserver")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)
