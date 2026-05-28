import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'account', 'OrdersPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن دکمه رهگیری کنار دکمه پیش‌فاکتور
old = """                  <button onClick={() => setSelectedOrder(order)}
                    className="text-xs px-4 py-2 rounded-xl border border-brand/30 text-brand dark:text-cyan hover:bg-brand/10 transition-colors">
                    📄 پیش‌فاکتور
                  </button>"""

new = """                  <div className="flex gap-2">
                    {order.tracking_code && (
                      <Link to={`/track/${order.order_number}`}
                        className="text-xs px-4 py-2 rounded-xl border border-green-500/30 text-green-400 hover:bg-green-500/10 transition-colors">
                        🚚 رهگیری
                      </Link>
                    )}
                    <button onClick={() => setSelectedOrder(order)}
                      className="text-xs px-4 py-2 rounded-xl border border-brand/30 text-brand dark:text-cyan hover:bg-brand/10 transition-colors">
                      📄 پیش‌فاکتور
                    </button>
                  </div>"""

if old in content:
    content = content.replace(old, new)
    print("✓ دکمه رهگیری اضافه شد")
else:
    print("✗ متن پیدا نشد")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)

# ─── اصلاح Admin — نمایش نام و آدرس مشتری ───────────────────
admin_path = os.path.join('apps', 'orders', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    admin = f.read()

if 'get_customer_name' not in admin:
    old_admin = """@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ["order_number", "user", "status", "delivery_status",
                     "courier_company", "tracking_code", "created_at"]"""

    new_admin = """@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ["order_number", "get_customer_name", "get_customer_phone",
                     "status", "delivery_status", "courier_company", "tracking_code", "created_at"]

    def get_customer_name(self, obj):
        return obj.user.get_full_name() or '—'
    get_customer_name.short_description = "نام مشتری"

    def get_customer_phone(self, obj):
        return obj.user.phone or '—'
    get_customer_phone.short_description = "موبایل" """

    if old_admin in admin:
        admin = admin.replace(old_admin, new_admin)
        with open(admin_path, 'w', encoding='utf-8') as f:
            f.write(admin)
        print("✓ نام و موبایل مشتری به Admin اضافه شد")
    else:
        print("✗ OrderAdmin پیدا نشد")

# اضافه کردن آدرس به fieldsets سفارش
if 'shipping_address' not in admin:
    with open(admin_path, encoding='utf-8') as f:
        admin = f.read()
    admin = admin.replace(
        '("یادداشت‌ها", {"fields": ("admin_notes",)}),',
        '("آدرس ارسال", {"fields": ("shipping_address",)}),\n        ("یادداشت‌ها", {"fields": ("admin_notes",)}),'
    )
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(admin)
    print("✓ آدرس ارسال به Admin اضافه شد")

print("done")
