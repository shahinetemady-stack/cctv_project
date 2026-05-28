import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

old = '''        # فاکتورهای خرید (به عنوان تامین‌کننده)
        supplier_invoices = [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "role": "supplier",
            "description": "فاکتور خرید کالا",
            "amount_cny": float(sum(
                float(item.unit_price_cny) * item.quantity
                for item in inv.items.all()
            )),
            "amount_irr": int(sum(
                float(item.unit_price_cny) * inv.rate_purchase_cny * item.quantity
                for item in inv.items.all()
            )),
        } for inv in c.purchase_invoices.order_by("-date")[:20]]'''

new = '''        # فاکتورهای خرید (به عنوان تامین‌کننده) — فقط یوان، بدون ریال
        supplier_invoices = [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "role": "supplier",
            "description": f"فاکتور خرید کالا {inv.invoice_number or inv.id}",
            "amount_cny": float(sum(
                float(item.unit_price_cny) * item.quantity
                for item in inv.items.all()
            )),
            "amount_irr": 0,  # تامین‌کننده چینی — بدهی به یوان، نه ریال
        } for inv in c.purchase_invoices.order_by("-date")[:20]]'''

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ views.py اصلاح شد")
else:
    print("✗ متن پیدا نشد")
    import sys; sys.exit(1)

print("✓ سرور را restart کنید")
