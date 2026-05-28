import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

old = '''        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr,
            "reference": p.reference, "note": p.note,
            "invoice_id": p.invoice_id,
        } for p in c.payments.order_by("-date")[:50]]

        invoices = [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
        } for inv in c.purchase_invoices.order_by("-date")[:20]]

        return Response({
            "id": c.id, "name": c.name,
            "contact_type": c.contact_type,
            "contact_type_display": c.get_contact_type_display(),
            "currency": c.currency,
            "phone": c.phone, "wechat": c.wechat,
            "balance_irr": c.balance_irr,
            "balance_cny": float(c.balance_cny),
            "payments": payments,
            "invoices": invoices,
        })'''

new = '''        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr,
            "reference": p.reference, "note": p.note,
            "invoice_id": p.invoice_id,
        } for p in c.payments.order_by("-date")[:50]]

        # فاکتورهای خرید (به عنوان تامین‌کننده)
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
        } for inv in c.purchase_invoices.order_by("-date")[:20]]

        # فاکتورهای حمل (به عنوان شرکت حمل/ترخیص‌کار)
        shipping_invoices = [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "role": "shipper",
            "description": f"حمل و ترخیص — فاکتور {inv.invoice_number or inv.id}",
            "amount_cny": float(inv.shipping_cost_cny),
            "amount_irr": inv.clearance_cost_irr,
        } for inv in c.shipping_invoices.order_by("-date")[:20]]

        invoices = supplier_invoices + shipping_invoices
        invoices.sort(key=lambda x: x["date"], reverse=True)

        return Response({
            "id": c.id, "name": c.name,
            "contact_type": c.contact_type,
            "contact_type_display": c.get_contact_type_display(),
            "currency": c.currency,
            "phone": c.phone, "wechat": c.wechat,
            "balance_irr": c.balance_irr,
            "balance_cny": float(c.balance_cny),
            "payments": payments,
            "invoices": invoices,
        })'''

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ views.py اصلاح شد")
else:
    print("✗ متن پیدا نشد")
    import sys; sys.exit(1)

# تست API
print("\nتست ContactDetailView:")
from apps.accounting.models import Contact
for c in Contact.objects.filter(is_active=True):
    print(f"\n{c.name}:")
    print(f"  فاکتورهای تامین‌کننده: {c.purchase_invoices.count()}")
    print(f"  فاکتورهای حمل: {c.shipping_invoices.count()}")
    print(f"  پرداخت‌ها: {c.payments.count()}")
    print(f"  مانده ریال: {c.balance_irr:,.0f}")
    print(f"  مانده یوان: {c.balance_cny:.2f}")

print("\n✓ سرور را restart کنید")
