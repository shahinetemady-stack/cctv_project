import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

old = '''    def get(self, request, variant_id):
        from apps.catalog.models import ProductVariant
        try:
            v = ProductVariant.objects.get(id=variant_id, is_active=True)
            # قیمت عمومی سایت
            public_price = v.final_price

            # قیمت همکار (اگر کاربر همکار است)
            partner_price = None
            if request.user.is_authenticated:
                try:
                    disc = float(request.user.profile.discount_percent or 0)
                    if disc > 0:
                        import math
                        partner_price = math.ceil(public_price * (1 - disc / 100))
                except Exception:
                    pass

            return Response({
                'variant_id': variant_id,
                'sku': v.sku,
                'public_price': public_price,
                'partner_price': partner_price,
                'suggested_price': partner_price or public_price,
            })
        except ProductVariant.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)'''

new = '''    def get(self, request, variant_id):
        from apps.catalog.models import ProductVariant
        import math
        try:
            v = ProductVariant.objects.get(id=variant_id, is_active=True)
            public_price = v.final_price

            # قیمت همکار بر اساس customer_id که از فرانت می‌آید
            partner_price = None
            customer_id = request.query_params.get('customer_id')
            if customer_id:
                try:
                    from apps.users.models import User
                    customer = User.objects.get(id=customer_id)
                    disc = float(customer.profile.discount_percent or 0)
                    if disc > 0:
                        partner_price = math.ceil(public_price * (1 - disc / 100))
                except Exception:
                    pass

            return Response({
                'variant_id': variant_id,
                'sku': v.sku,
                'public_price': public_price,
                'partner_price': partner_price,
                'suggested_price': partner_price or public_price,
                'is_partner_price': partner_price is not None,
            })
        except ProductVariant.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)'''

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ VariantPriceView اصلاح شد")
else:
    print("✗ متن پیدا نشد")
    idx = content.find('VariantPriceView')
    print(repr(content[idx:idx+200]))

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-200:])
