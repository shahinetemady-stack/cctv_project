import os

with open(os.path.join('apps','orders','admin.py'), encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '    list_filter  = ["status", "order_type", "shipping_method",\n                    ("created_at", admin.DateFieldListFilter)]',
    '    list_filter  = ["status", "order_type",\n                    ("created_at", admin.DateFieldListFilter)]'
)

with open(os.path.join('apps','orders','admin.py'), 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")

import subprocess, sys
r = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'], capture_output=True, text=True)
print("OK - check" if r.returncode == 0 else (r.stdout+r.stderr)[-200:])
