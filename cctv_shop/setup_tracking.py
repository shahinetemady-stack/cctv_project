"""
python setup_tracking.py
سیستم رهگیری مرسوله
"""
import os, sys, subprocess

# ─── 1. اضافه کردن فیلدها به Order ───────────────────────────
migration_code = '''
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0006_alter_order_freight_company_alter_order_paid_amount_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='order',
            name='courier_company',
            field=models.CharField(
                max_length=20, blank=True, default='',
                choices=[
                    ('post', 'پست'),
                    ('tipax', 'تیپاکس'),
                    ('chapar', 'چاپار'),
                    ('snap', 'اسنپ‌باکس'),
                    ('other', 'سایر'),
                ],
                verbose_name='شرکت پیک/پست',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='shipped_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='تاریخ ارسال'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivered_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تحویل'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_status',
            field=models.CharField(
                max_length=20, default='pending',
                choices=[
                    ('pending', 'در انتظار ارسال'),
                    ('shipped', 'ارسال شده'),
                    ('in_transit', 'در مسیر'),
                    ('delivered', 'تحویل داده شده'),
                    ('returned', 'مرجوع شده'),
                ],
                verbose_name='وضعیت ارسال',
                db_index=True,
            ),
        ),
    ]
'''

# پیدا کردن آخرین migration orders
migrations_dir = os.path.join('apps', 'orders', 'migrations')
existing = [f for f in os.listdir(migrations_dir) if f.endswith('.py') and f != '__init__.py']
existing.sort()
last = existing[-1].replace('.py', '')
print(f"Last migration: {last}")

# ساخت migration جدید
new_migration_path = os.path.join(migrations_dir, '0007_order_tracking_fields.py')
if not os.path.exists(new_migration_path):
    migration_code = migration_code.replace(
        "('orders', '0006_alter_order_freight_company_alter_order_paid_amount_and_more')",
        f"('orders', '{last}')"
    )
    with open(new_migration_path, 'w', encoding='utf-8') as f:
        f.write(migration_code)
    print("✓ migration ساخته شد")

r = subprocess.run([sys.executable, 'manage.py', 'migrate', 'orders'],
                   capture_output=True, text=True)
print(r.stdout[-200:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:", r.stderr[-400:])

# ─── 2. View برای tracking ────────────────────────────────────
views_path = os.path.join('apps', 'orders', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

tracking_view = '''

class OrderTrackingView(APIView):
    """GET /api/orders/<order_number>/track/ — رهگیری سفارش"""
    permission_classes = [AllowAny]

    def get(self, request, order_number):
        from .models import Order
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=404)

        # بررسی دسترسی — فقط صاحب سفارش یا ادمین
        if not request.user.is_staff:
            if not request.user.is_authenticated or request.user.id != order.user_id:
                # فقط اطلاعات عمومی
                if not order.tracking_code:
                    return Response({'error': 'اطلاعات رهگیری موجود نیست'}, status=404)

        # وضعیت‌های مرحله به مرحله
        steps = [
            {'key': 'pending',    'label': 'ثبت سفارش',        'icon': '📋'},
            {'key': 'confirmed',  'label': 'تأیید سفارش',       'icon': '✅'},
            {'key': 'shipped',    'label': 'ارسال شده',          'icon': '📦'},
            {'key': 'in_transit', 'label': 'در مسیر',           'icon': '🚚'},
            {'key': 'delivered',  'label': 'تحویل داده شده',    'icon': '🎉'},
        ]

        delivery_status = getattr(order, 'delivery_status', 'pending')
        step_keys = [s['key'] for s in steps]
        current_idx = step_keys.index(delivery_status) if delivery_status in step_keys else 0

        for i, step in enumerate(steps):
            step['done'] = i <= current_idx
            step['current'] = i == current_idx

        return Response({
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'delivery_status': delivery_status,
            'tracking_code': getattr(order, 'tracking_code', '') or order.tracking_code,
            'courier_company': getattr(order, 'courier_company', ''),
            'courier_display': dict([
                ('post', 'پست'), ('tipax', 'تیپاکس'),
                ('chapar', 'چاپار'), ('snap', 'اسنپ‌باکس'), ('other', 'سایر')
            ]).get(getattr(order, 'courier_company', ''), ''),
            'shipped_at': order.shipped_at.strftime('%Y-%m-%d %H:%M') if getattr(order, 'shipped_at', None) else None,
            'delivered_at': order.delivered_at.strftime('%Y-%m-%d %H:%M') if getattr(order, 'delivered_at', None) else None,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'steps': steps,
            'items_count': order.items.count(),
            'total': order.effective_amount,
        })
'''

if 'OrderTrackingView' not in views:
    views += tracking_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ OrderTrackingView اضافه شد")

# ─── 3. URL ───────────────────────────────────────────────────
urls_path = os.path.join('apps', 'orders', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'track' not in urls:
    idx = urls.rfind(']')
    urls = urls[:idx] + "    path('<str:order_number>/track/', views.OrderTrackingView.as_view()),\n" + urls[idx:]
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ URL tracking اضافه شد")

# ─── 4. Admin ─────────────────────────────────────────────────
orders_admin = os.path.join('apps', 'orders', 'admin.py')
with open(orders_admin, encoding='utf-8') as f:
    admin = f.read()

if 'OrderAdmin' not in admin and 'delivery_status' not in admin:
    admin += '''

from apps.orders.models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ["order_number", "user", "status", "delivery_status",
                     "courier_company", "tracking_code", "created_at"]
    list_filter   = ["status", "delivery_status", "courier_company"]
    search_fields = ["order_number", "user__phone", "tracking_code"]
    list_editable = ["delivery_status", "courier_company"]
    readonly_fields = ["order_number", "created_at", "updated_at"]
    fieldsets = (
        ("اطلاعات سفارش", {"fields": ("order_number", "user", "status", "total_amount")}),
        ("ارسال", {"fields": (
            "courier_company", "tracking_code", "delivery_status",
            "shipped_at", "delivered_at",
        )}),
        ("یادداشت‌ها", {"fields": ("admin_notes",)}),
    )
'''
    with open(orders_admin, 'w', encoding='utf-8') as f:
        f.write(admin)
    print("✓ OrderAdmin اضافه شد")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r3.returncode == 0 else r3.stderr[-300:])
