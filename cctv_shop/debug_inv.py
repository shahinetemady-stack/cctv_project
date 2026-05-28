import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounting.models import PurchaseInvoice, Contact

inv = PurchaseInvoice.objects.first()
print(f"فاکتور #{inv.id}")
print(f"تامین‌کننده: {inv.supplier.name}")
print(f"نرخ خرید: {inv.rate_purchase_cny}")
print(f"نرخ حمل: {inv.rate_shipping_cny}")
print(f"حمل یوان: {inv.shipping_cost_cny}")
print(f"ترخیص ریال: {inv.clearance_cost_irr}")
print()

for item in inv.items.all():
    calc = float(item.unit_price_cny) * inv.rate_purchase_cny * item.quantity
    print(f"کالا: qty={item.quantity} | price_cny={item.unit_price_cny} | rate={inv.rate_purchase_cny}")
    print(f"  => {item.quantity} × {item.unit_price_cny} × {inv.rate_purchase_cny} = {calc:,.0f}")

print()
print("--- balance های فعلی ---")
for c in Contact.objects.filter(is_active=True):
    print(f"{c.name} [{c.contact_type}]: IRR={c.balance_irr:,.0f} | CNY={c.balance_cny:.2f}")
