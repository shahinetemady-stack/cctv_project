"""
python setup_sales.py
ساخت سیستم فروش + گزارش سود/زیان + تراز کلی
اجرا در پوشه cctv_shop
"""
import os, sys, subprocess

# ─── 1. models.py — اضافه کردن SaleInvoice به accounting ────
models_path = os.path.join('apps', 'accounting', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

sale_models = '''

def generate_invoice_number(prefix='INV'):
    """شماره فاکتور خودکار: INV-YYYYMMDD-XXXX"""
    from django.utils import timezone
    import uuid
    today = timezone.now().strftime("%Y%m%d")
    short = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{today}-{short}"


class SaleInvoice(models.Model):
    """فاکتور فروش — هم از سفارش سایت، هم دستی"""

    class Status(models.TextChoices):
        DRAFT     = "draft",     "پیش‌نویس"
        CONFIRMED = "confirmed", "تأیید شده"
        PAID      = "paid",      "تسویه شده"
        CANCELLED = "cancelled", "لغو شده"

    class InvoiceSource(models.TextChoices):
        ORDER  = "order",  "سفارش سایت"
        MANUAL = "manual", "دستی (خارج از سایت)"

    # شماره و هویت
    invoice_number = models.CharField(max_length=50, unique=True,
                        default=generate_invoice_number, verbose_name="شماره فاکتور")
    source    = models.CharField(max_length=10, choices=InvoiceSource.choices,
                    default=InvoiceSource.MANUAL, verbose_name="منبع")

    # لینک به سفارش سایت (اختیاری)
    order     = models.OneToOneField('orders.Order', on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='sale_invoice',
                    verbose_name="سفارش سایت")

    # مشتری
    customer  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                    related_name='sale_invoices', verbose_name="مشتری")
    customer_name = models.CharField(max_length=200, blank=True, verbose_name="نام مشتری")
    customer_phone = models.CharField(max_length=20, blank=True, verbose_name="تلفن")

    # مالی
    discount_amount = models.PositiveBigIntegerField(default=0, verbose_name="تخفیف (ریال)")
    shipping_cost   = models.PositiveBigIntegerField(default=0, verbose_name="هزینه ارسال (ریال)")
    tax_amount      = models.PositiveBigIntegerField(default=0, verbose_name="مالیات (ریال)")
    note      = models.TextField(blank=True, verbose_name="توضیحات")
    status    = models.CharField(max_length=20, choices=Status.choices,
                    default=Status.DRAFT, verbose_name="وضعیت")

    # ثبت‌کننده
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='created_invoices',
                    verbose_name="صادرکننده")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounting_sale_invoice"
        verbose_name = "فاکتور فروش"
        verbose_name_plural = "فاکتورهای فروش"
        ordering = ["-created_at"]

    def __str__(self):
        return f"فاکتور {self.invoice_number} — {self.customer_name or self.customer}"

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_amount(self):
        return self.subtotal - self.discount_amount + self.shipping_cost + self.tax_amount

    @property
    def paid_amount(self):
        from django.db.models import Sum
        return self.sale_payments.aggregate(s=Sum('amount'))['s'] or 0

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    @property
    def total_cost(self):
        """بهای تمام شده کل فاکتور"""
        return sum(item.total_cost for item in self.items.all())

    @property
    def gross_profit(self):
        """سود ناخالص ریالی"""
        return self.total_amount - self.total_cost


class SaleItem(models.Model):
    """آیتم فاکتور فروش"""
    invoice   = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE,
                    related_name='items', verbose_name="فاکتور")
    variant   = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT,
                    related_name='sale_items', verbose_name="کالا")
    quantity  = models.PositiveIntegerField(verbose_name="تعداد")
    unit_price = models.PositiveBigIntegerField(verbose_name="قیمت واحد (ریال)")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                        verbose_name="تخفیف (%)")

    class Meta:
        db_table = "accounting_sale_item"
        verbose_name = "آیتم فاکتور فروش"
        verbose_name_plural = "آیتم‌های فاکتور فروش"

    def __str__(self):
        return f"{self.variant} × {self.quantity}"

    @property
    def subtotal(self):
        disc = self.unit_price * self.quantity * float(self.discount_percent) / 100
        return int(self.unit_price * self.quantity - disc)

    @property
    def unit_cost(self):
        """بهای تمام شده واحد از آخرین فاکتور خرید"""
        item = self.variant.purchase_items.order_by('-invoice__date').first()
        return item.unit_cost_irr if item else 0

    @property
    def total_cost(self):
        return self.unit_cost * self.quantity

    @property
    def profit(self):
        return self.subtotal - self.total_cost


class SalePayment(models.Model):
    """پرداخت مشتری بابت فاکتور فروش"""

    class PaymentMethod(models.TextChoices):
        CASH     = "cash",     "نقد"
        TRANSFER = "transfer", "حواله بانکی"
        CARD     = "card",     "کارت به کارت"
        ONLINE   = "online",   "پرداخت آنلاین"
        CREDIT   = "credit",   "نسیه (حساب باز)"

    invoice    = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE,
                    related_name='sale_payments', verbose_name="فاکتور")
    to_account = models.ForeignKey('Account', on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='sale_receipts',
                    verbose_name="به حساب (بانک/صندوق)")
    method     = models.CharField(max_length=20, choices=PaymentMethod.choices,
                    verbose_name="روش پرداخت")
    amount     = models.PositiveBigIntegerField(verbose_name="مبلغ (ریال)")
    date       = models.DateField(verbose_name="تاریخ")
    reference  = models.CharField(max_length=100, blank=True, verbose_name="شماره پیگیری")
    note       = models.TextField(blank=True, verbose_name="توضیحات")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, verbose_name="ثبت‌کننده")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounting_sale_payment"
        verbose_name = "پرداخت فروش"
        verbose_name_plural = "پرداخت‌های فروش"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.invoice.invoice_number} | {self.amount:,} ریال | {self.get_method_display()}"
'''

if 'class SaleInvoice' not in content:
    content += sale_models
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ models.py — SaleInvoice اضافه شد")
else:
    print("✓ SaleInvoice قبلاً موجود بود")

# ─── 2. آپدیت views.py ───────────────────────────────────────
views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

sale_views = '''

# ─── Sale Invoices ───────────────────────────────────────────

class SaleInvoiceListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import SaleInvoice
        qs = SaleInvoice.objects.select_related(
            'customer', 'created_by', 'order'
        ).order_by('-created_at')[:100]
        data = [{
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'source': inv.source,
            'source_display': inv.get_source_display(),
            'customer_name': inv.customer_name or str(inv.customer),
            'customer_phone': inv.customer_phone,
            'status': inv.status,
            'status_display': inv.get_status_display(),
            'subtotal': inv.subtotal,
            'discount_amount': inv.discount_amount,
            'shipping_cost': inv.shipping_cost,
            'total_amount': inv.total_amount,
            'paid_amount': inv.paid_amount,
            'remaining_amount': inv.remaining_amount,
            'total_cost': inv.total_cost,
            'gross_profit': inv.gross_profit,
            'items_count': inv.items.count(),
            'created_by': str(inv.created_by) if inv.created_by else '',
            'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M'),
            'order_number': inv.order.order_number if inv.order else '',
        } for inv in qs]
        return Response(data)

    def post(self, request):
        from .models import SaleInvoice, SaleItem
        from apps.catalog.models import ProductVariant
        d = request.data
        try:
            # پیدا کردن یا ساختن کاربر
            from apps.users.models import User
            customer_id = d.get('customer_id')
            if customer_id:
                customer = User.objects.get(id=customer_id)
            else:
                return Response({'error': 'customer_id الزامی است'}, status=400)

            inv = SaleInvoice.objects.create(
                source=d.get('source', 'manual'),
                order_id=d.get('order_id') or None,
                customer=customer,
                customer_name=d.get('customer_name', str(customer)),
                customer_phone=d.get('customer_phone', ''),
                discount_amount=int(d.get('discount_amount', 0)),
                shipping_cost=int(d.get('shipping_cost', 0)),
                tax_amount=int(d.get('tax_amount', 0)),
                note=d.get('note', ''),
                status=d.get('status', 'draft'),
                created_by=request.user,
            )

            for item_d in d.get('items', []):
                SaleItem.objects.create(
                    invoice=inv,
                    variant_id=item_d['variant_id'],
                    quantity=int(item_d['quantity']),
                    unit_price=int(item_d['unit_price']),
                    discount_percent=item_d.get('discount_percent', 0),
                )

            return Response({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'total_amount': inv.total_amount,
                'message': 'فاکتور با موفقیت صادر شد',
            }, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class SaleInvoiceDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        from .models import SaleInvoice
        try:
            inv = SaleInvoice.objects.select_related(
                'customer', 'created_by', 'order'
            ).get(pk=pk)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)

        items = [{
            'id': item.id,
            'variant_id': item.variant_id,
            'variant_sku': item.variant.sku,
            'product_name': item.variant.product.name,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'discount_percent': float(item.discount_percent),
            'subtotal': item.subtotal,
            'unit_cost': item.unit_cost,
            'total_cost': item.total_cost,
            'profit': item.profit,
        } for item in inv.items.select_related('variant__product').all()]

        payments = [{
            'id': p.id,
            'method': p.method,
            'method_display': p.get_method_display(),
            'amount': p.amount,
            'date': str(p.date),
            'reference': p.reference,
            'to_account': p.to_account.name if p.to_account else '',
            'created_by': str(p.created_by) if p.created_by else '',
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
        } for p in inv.sale_payments.all()]

        return Response({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'source': inv.source,
            'source_display': inv.get_source_display(),
            'customer_id': inv.customer_id,
            'customer_name': inv.customer_name or str(inv.customer),
            'customer_phone': inv.customer_phone,
            'status': inv.status,
            'status_display': inv.get_status_display(),
            'subtotal': inv.subtotal,
            'discount_amount': inv.discount_amount,
            'shipping_cost': inv.shipping_cost,
            'tax_amount': inv.tax_amount,
            'total_amount': inv.total_amount,
            'paid_amount': inv.paid_amount,
            'remaining_amount': inv.remaining_amount,
            'total_cost': inv.total_cost,
            'gross_profit': inv.gross_profit,
            'note': inv.note,
            'created_by': str(inv.created_by) if inv.created_by else '',
            'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M'),
            'order_number': inv.order.order_number if inv.order else '',
            'items': items,
            'payments': payments,
        })

    def patch(self, request, pk):
        from .models import SaleInvoice
        try:
            inv = SaleInvoice.objects.get(pk=pk)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        if 'status' in request.data:
            inv.status = request.data['status']
            inv.save()
        return Response({'id': inv.id, 'status': inv.status})


class SalePaymentCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .models import SaleInvoice, SalePayment
        d = request.data
        try:
            inv = SaleInvoice.objects.get(id=d['invoice_id'])
            p = SalePayment.objects.create(
                invoice=inv,
                to_account_id=d.get('to_account_id') or None,
                method=d.get('method', 'transfer'),
                amount=int(d['amount']),
                date=d['date'],
                reference=d.get('reference', ''),
                note=d.get('note', ''),
                created_by=request.user,
            )
            # اگر کاملاً تسویه شد وضعیت را تغییر بده
            if inv.remaining_amount <= 0:
                inv.status = 'paid'
                inv.save()
            return Response({
                'id': p.id,
                'remaining': inv.remaining_amount,
                'message': 'پرداخت ثبت شد',
            }, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ─── Pending Orders (پیش‌فاکتورهای سایت) ───────────────────

class PendingOrdersView(APIView):
    """لیست سفارشات تایید نشده برای تبدیل به فاکتور"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.orders.models import Order, OrderItem
        qs = Order.objects.filter(
            status__in=['pending', 'confirmed', 'awaiting_payment']
        ).select_related('user').prefetch_related('items__variant__product')[:50]

        data = [{
            'id': o.id,
            'order_number': o.order_number,
            'customer_name': str(o.user),
            'customer_phone': o.user.phone if hasattr(o.user, 'phone') else '',
            'order_type': o.order_type,
            'order_type_display': o.get_order_type_display(),
            'status': o.status,
            'status_display': o.get_status_display(),
            'total_amount': o.effective_amount,
            'has_invoice': hasattr(o, 'sale_invoice'),
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
            'items': [{
                'variant_id': item.variant_id,
                'product_name': item.variant.product.name,
                'sku': item.variant.sku,
                'quantity': item.quantity,
                'unit_price': item.confirmed_unit_price or item.unit_price,
            } for item in o.items.all()],
        } for o in qs]
        return Response(data)


# ─── Profit Report ───────────────────────────────────────────

class ProfitReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import SaleInvoice
        from apps.catalog.models import ExchangeRateSetting
        from django.db.models import Sum

        invoices = SaleInvoice.objects.filter(
            status__in=['confirmed', 'paid']
        ).prefetch_related('items__variant__purchase_items__invoice')

        total_revenue = 0
        total_cost    = 0
        total_profit  = 0
        items_report  = []

        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt // 10  # تبدیل به تومان

        for inv in invoices:
            for item in inv.items.all():
                revenue  = item.subtotal
                cost     = item.total_cost
                profit   = item.profit
                # سود یوانی = (قیمت فروش - بهای تمام شده) / نرخ یوان روز
                profit_cny = profit / rate if rate else 0

                total_revenue += revenue
                total_cost    += cost
                total_profit  += profit

                items_report.append({
                    'product': item.variant.product.name,
                    'sku': item.variant.sku,
                    'invoice_number': inv.invoice_number,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'unit_cost': item.unit_cost,
                    'profit_per_unit': item.profit // item.quantity if item.quantity else 0,
                    'profit_total': profit,
                    'profit_cny': round(profit_cny, 2),
                })

        return Response({
            'summary': {
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'profit_margin': round(total_profit / total_revenue * 100, 1) if total_revenue else 0,
                'exchange_rate': rate,
                'total_profit_cny': round(total_profit / rate, 2) if rate else 0,
            },
            'items': items_report,
        })


# ─── Balance Sheet (تراز کلی) ────────────────────────────────

class BalanceSheetView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import SaleInvoice, Account, Contact, Payment
        from apps.inventory.models import WarehouseStock
        from apps.catalog.models import ExchangeRateSetting
        from django.db.models import Sum

        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt // 10

        # ─── دارایی‌ها ───────────────────────────────────────
        # ۱. موجودی کالا به بهای تمام شده
        stock_value = 0
        for stock in WarehouseStock.objects.select_related('variant').filter(quantity__gt=0):
            purchase_item = stock.variant.purchase_items.order_by('-invoice__date').first()
            cost = purchase_item.unit_cost_irr if purchase_item else 0
            stock_value += cost * stock.quantity

        # ۲. طلب از مشتریان (فاکتورهای فروش تسویه نشده)
        receivable = sum(
            inv.remaining_amount
            for inv in SaleInvoice.objects.filter(status__in=['confirmed', 'paid'])
            if inv.remaining_amount > 0
        )

        # ۳. موجودی حساب‌های بانکی/صندوق
        accounts = Account.objects.filter(is_active=True)
        cash_total = sum(a.balance for a in accounts if a.currency == 'IRR')
        cash_cny   = sum(a.balance for a in accounts if a.currency == 'CNY')

        total_assets = stock_value + receivable + cash_total + int(cash_cny * rate)

        # ─── بدهی‌ها ─────────────────────────────────────────
        # بدهی به تامین‌کنندگان و شرکت‌های حمل
        payable_irr = sum(
            c.balance_irr for c in Contact.objects.filter(is_active=True)
            if c.balance_irr > 0
        )
        payable_cny = sum(
            c.balance_cny for c in Contact.objects.filter(is_active=True)
            if c.balance_cny > 0
        )
        total_liabilities = payable_irr + int(payable_cny * rate)

        # ─── سود/زیان ────────────────────────────────────────
        paid_invoices = SaleInvoice.objects.filter(status__in=['confirmed', 'paid'])
        total_revenue = sum(inv.total_amount for inv in paid_invoices)
        total_cost_sold = sum(inv.total_cost for inv in paid_invoices)
        gross_profit = total_revenue - total_cost_sold

        equity = total_assets - total_liabilities

        return Response({
            'assets': {
                'stock_value': stock_value,
                'receivable': receivable,
                'cash_irr': cash_total,
                'cash_cny': cash_cny,
                'cash_cny_irr': int(cash_cny * rate),
                'total': total_assets,
            },
            'liabilities': {
                'payable_irr': payable_irr,
                'payable_cny': payable_cny,
                'payable_cny_irr': int(payable_cny * rate),
                'total': total_liabilities,
            },
            'equity': equity,
            'profit': {
                'total_revenue': total_revenue,
                'total_cost': total_cost_sold,
                'gross_profit': gross_profit,
                'margin': round(gross_profit / total_revenue * 100, 1) if total_revenue else 0,
                'gross_profit_cny': round(gross_profit / rate, 2) if rate else 0,
            },
            'exchange_rate': rate,
        })


# ─── Customer Search ─────────────────────────────────────────

class CustomerSearchView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import User
        q = request.query_params.get('q', '')
        if len(q) < 2:
            return Response([])
        users = User.objects.filter(
            models.Q(phone__icontains=q) |
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q)
        )[:10]
        return Response([{
            'id': u.id,
            'name': str(u),
            'phone': u.phone,
        } for u in users])
'''

if 'class SaleInvoiceListView' not in views:
    # اضافه کردن import مورد نیاز
    views = views.replace(
        'from django.db.models import Sum, Q',
        'from django.db.models import Sum, Q\nfrom django.db import models'
    )
    if 'from django.db import models' not in views:
        views = 'from django.db import models\n' + views
    views += sale_views
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ views.py — Sale views اضافه شد")
else:
    print("✓ Sale views قبلاً موجود بود")

# ─── 3. آپدیت urls.py ────────────────────────────────────────
urls_path = os.path.join('apps', 'accounting', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

new_urls = [
    ("sale-invoices/", "SaleInvoiceListView"),
    ("sale-invoices/<int:pk>/", "SaleInvoiceDetailView"),
    ("sale-payments/", "SalePaymentCreateView"),
    ("pending-orders/", "PendingOrdersView"),
    ("reports/profit/", "ProfitReportView"),
    ("reports/balance-sheet/", "BalanceSheetView"),
    ("customers/search/", "CustomerSearchView"),
]

added = []
for path_str, view_name in new_urls:
    if path_str not in urls:
        added.append(f"    path('{path_str}', views.{view_name}.as_view()),")

if added:
    urls = urls.rstrip()
    if urls.endswith(']'):
        urls = urls[:-1] + ',\n' + '\n'.join(added) + '\n]'
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print(f"✓ urls.py — {len(added)} مسیر اضافه شد")

# ─── 4. Migration ─────────────────────────────────────────────
r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'accounting'],
                   capture_output=True, text=True)
print(r.stdout[-400:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:"); print(r.stderr[-500:])
else:
    r2 = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                        capture_output=True, text=True)
    print(r2.stdout[-300:] if r2.stdout else "")
    if r2.returncode != 0:
        print("خطا migrate:"); print(r2.stderr[-500:])

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
if r3.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print((r3.stdout + r3.stderr)[-600:])
