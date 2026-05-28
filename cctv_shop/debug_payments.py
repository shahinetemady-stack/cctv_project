import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounting.models import Payment, Contact

print("=== همه پرداخت‌ها ===")
for p in Payment.objects.select_related('contact', 'invoice').all():
    print(f"  ID={p.id} | طرف={p.contact.name if p.contact else 'ندارد'} | {p.direction} | {p.amount} {p.currency} | فاکتور={p.invoice_id}")

print("\n=== balance درست ===")
print("zizi (supplier_cn):")
print("  بدهکار ریال = ارزش کالا = 1000 × 40 × 27000 = 1,080,000,000")
print("  بدهکار یوان = 1000 × 40 = 40,000 یوان")
print("  منهای پرداخت‌ها")

print("\nmad amvaj (shipping_co):")
print("  بدهکار ریال = ترخیص = 4,500,000")
print("  بدهکار یوان = حمل = 540 یوان")
print("  منهای پرداخت‌ها")
