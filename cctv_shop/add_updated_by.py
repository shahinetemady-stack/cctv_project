import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# ─── 1. اضافه کردن فیلد updated_by به دیتابیس ───────────────
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = {c[1] for c in cursor.fetchall()}

    if 'updated_by_id' not in cols:
        cursor.execute("ALTER TABLE orders_order ADD COLUMN updated_by_id INTEGER REFERENCES users_user(id)")
        cursor.execute("ALTER TABLE orders_order ADD COLUMN status_updated_at DATETIME")
        print("✓ فیلدهای updated_by و status_updated_at اضافه شد")
    else:
        print("✓ قبلاً موجود بود")

# ─── 2. اضافه کردن به Order model ────────────────────────────
models_path = os.path.join('apps', 'orders', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

if 'updated_by' not in content:
    content = content.replace(
        '    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name=\'تاریخ تحویل\')',
        '''    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تحویل')
    updated_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_orders', verbose_name='آپدیت شده توسط'
    )
    status_updated_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ آخرین تغییر وضعیت')'''
    )
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ updated_by به مدل اضافه شد")

# ─── 3. آپدیت AdminOrderUpdateView ───────────────────────────
views_path = os.path.join('apps', 'orders', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

old_save = '''        order.save()
        return Response({'ok': True, 'order_number': order.order_number})'''

new_save = '''        order.updated_by = request.user
        order.status_updated_at = timezone.now()
        order.save()
        return Response({'ok': True, 'order_number': order.order_number})'''

if old_save in views:
    views = views.replace(old_save, new_save)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ updated_by در view اضافه شد")

# ─── 4. آپدیت API برای برگرداندن updated_by ─────────────────
old_response = '''            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
        } for o in qs[:200]])'''

new_response = '''            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_by': o.updated_by.get_full_name() or o.updated_by.phone if o.updated_by else '',
            'status_updated_at': o.status_updated_at.strftime('%Y-%m-%d %H:%M') if o.status_updated_at else '',
        } for o in qs[:200]])'''

with open(views_path, encoding='utf-8') as f:
    views = f.read()

if old_response in views:
    views = views.replace(old_response, new_response)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ updated_by در response اضافه شد")

# ─── 5. fake migrate ─────────────────────────────────────────
import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
print("سرور را restart کنید")
