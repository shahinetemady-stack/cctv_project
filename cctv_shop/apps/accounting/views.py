"""
apps/accounting/views.py
API endpoints برای سیستم حسابداری
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum, Q
from django.db import models
from decimal import Decimal
from .models import Contact, PurchaseInvoice, PurchaseItem, ExtraCost, Payment




# ─── Accounts ────────────────────────────────────────────────

class AccountListView(APIView):
    """GET /api/accounting/accounts/ — لیست صندوق‌ها و حساب‌های بانکی"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import Account
        accounts = Account.objects.filter(is_active=True)
        return Response([{
            "id": a.id,
            "name": a.name,
            "account_type": a.account_type,
            "account_type_display": a.get_account_type_display(),
            "currency": a.currency,
            "bank_name": a.bank_name,
            "account_number": a.account_number,
            "balance": a.balance,
        } for a in accounts])

    def post(self, request):
        from .models import Account
        d = request.data
        a = Account.objects.create(
            name=d["name"],
            account_type=d.get("account_type", "cash"),
            currency=d.get("currency", "IRR"),
            bank_name=d.get("bank_name", ""),
            account_number=d.get("account_number", ""),
            initial_balance=d.get("initial_balance", 0),
            note=d.get("note", ""),
        )
        return Response({"id": a.id, "name": a.name}, status=201)

# ─── Contacts ────────────────────────────────────────────────

class ContactListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Contact.objects.filter(is_active=True)
        contact_type = request.query_params.get("type")
        if contact_type:
            qs = qs.filter(contact_type=contact_type)
        data = [{
            "id": c.id, "name": c.name,
            "contact_type": c.contact_type,
            "contact_type_display": c.get_contact_type_display(),
            "currency": c.currency,
            "phone": c.phone,
            "wechat": c.wechat,
            "balance_irr": c.balance_irr,
            "balance_cny": float(c.balance_cny),
        } for c in qs]
        return Response(data)

    def post(self, request):
        d = request.data
        c = Contact.objects.create(
            name=d["name"],
            contact_type=d["contact_type"],
            currency=d.get("currency", "CNY"),
            phone=d.get("phone", ""),
            wechat=d.get("wechat", ""),
            note=d.get("note", ""),
        )
        return Response({"id": c.id, "name": c.name}, status=201)


class ContactDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            c = Contact.objects.get(pk=pk)
        except Contact.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr,
            "reference": p.reference, "note": p.note,
            "invoice_id": p.invoice_id,
        } for p in c.payments.order_by("-date")[:50]]

        # فاکتورهای خرید (به عنوان تامین‌کننده) — فقط یوان، بدون ریال
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
        })


# ─── Purchase Invoices ───────────────────────────────────────

class PurchaseInvoiceListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = PurchaseInvoice.objects.select_related("supplier", "warehouse").order_by("-date")
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        data = [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "supplier_id": inv.supplier_id,
            "supplier_name": inv.supplier.name,
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "rate_purchase_cny": inv.rate_purchase_cny,
            "rate_shipping_cny": inv.rate_shipping_cny,
            "shipping_cost_cny": float(inv.shipping_cost_cny),
            "clearance_cost_irr": inv.clearance_cost_irr,
            "total_weight": inv.total_weight,
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
            "items_count": inv.items.count(),
        } for inv in qs[:100]]
        return Response(data)

    def post(self, request):
        d = request.data
        try:
            inv = PurchaseInvoice.objects.create(
                supplier_id=d["supplier_id"],
                invoice_number=d.get("invoice_number", ""),
                date=d["date"],
                warehouse_id=d.get("warehouse_id") or None,
                rate_purchase_cny=int(d["rate_purchase_cny"]),
                rate_shipping_cny=int(d["rate_shipping_cny"]),
                shipping_contact_id=d.get("shipping_contact_id") or None,
                shipping_cost_cny=Decimal(str(d.get("shipping_cost_cny", 0))),
                clearance_cost_irr=int(d.get("clearance_cost_irr", 0)),
                note=d.get("note", ""),
                created_by=request.user,
            )
            # ذخیره آیتم‌ها
            for item_data in d.get("items", []):
                PurchaseItem.objects.create(
                    invoice=inv,
                    variant_id=item_data["variant_id"],
                    quantity=int(item_data["quantity"]),
                    carton_count=int(item_data.get("carton_count", 1)),
                    carton_weight=Decimal(str(item_data["carton_weight"])),
                    unit_price_cny=Decimal(str(item_data["unit_price_cny"])),
                    note=item_data.get("note", ""),
                )
            # ذخیره هزینه‌های جانبی
            for extra in d.get("extra_costs", []):
                ExtraCost.objects.create(
                    invoice=inv,
                    cost_type=extra["cost_type"],
                    contact_id=extra.get("contact_id") or None,
                    amount_irr=int(extra["amount_irr"]),
                    description=extra.get("description", ""),
                    date=extra.get("date") or inv.date,
                )
            # محاسبه بهای تمام شده
            inv.calculate_items_cost()
            return Response({"id": inv.id, "message": "فاکتور با موفقیت ثبت شد"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class PurchaseInvoiceDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            inv = PurchaseInvoice.objects.select_related(
                "supplier", "warehouse", "shipping_contact"
            ).get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        items = [{
            "id": item.id,
            "variant_id": item.variant_id,
            "variant_sku": item.variant.sku,
            "product_name": item.variant.product.name,
            "quantity": item.quantity,
            "carton_count": item.carton_count,
            "carton_weight": float(item.carton_weight),
            "total_weight": item.total_weight,
            "unit_price_cny": float(item.unit_price_cny),
            "subtotal_cny": float(item.subtotal_cny),
            "shipping_cost_irr": item.shipping_cost_irr,
            "clearance_cost_irr": item.clearance_cost_irr,
            "extra_cost_irr": item.extra_cost_irr,
            "unit_cost_irr": item.unit_cost_irr,
            "note": item.note,
        } for item in inv.items.select_related("variant__product").all()]

        extra_costs = [{
            "id": e.id,
            "cost_type": e.cost_type,
            "cost_type_display": e.get_cost_type_display(),
            "contact_id": e.contact_id,
            "contact_name": e.contact.name if e.contact else "",
            "amount_irr": e.amount_irr,
            "description": e.description,
        } for e in inv.extra_costs.all()]

        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr, "reference": p.reference,
        } for p in inv.payments.all()]

        return Response({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "supplier": {"id": inv.supplier_id, "name": inv.supplier.name},
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "warehouse": {"id": inv.warehouse_id, "name": inv.warehouse.name} if inv.warehouse else None,
            "rate_purchase_cny": inv.rate_purchase_cny,
            "rate_shipping_cny": inv.rate_shipping_cny,
            "shipping_contact": {"id": inv.shipping_contact_id, "name": inv.shipping_contact.name} if inv.shipping_contact else None,
            "shipping_cost_cny": float(inv.shipping_cost_cny),
            "clearance_cost_irr": inv.clearance_cost_irr,
            "total_weight": inv.total_weight,
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
            "note": inv.note,
            "items": items,
            "extra_costs": extra_costs,
            "payments": payments,
        })

    def patch(self, request, pk):
        """آپدیت وضعیت فاکتور"""
        try:
            inv = PurchaseInvoice.objects.get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if "status" in request.data:
            inv.status = request.data["status"]
            inv.save()
        return Response({"id": inv.id, "status": inv.status})


# ─── Payments ────────────────────────────────────────────────

class PaymentCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        d = request.data
        try:
            p = Payment.objects.create(
                contact_id=d["contact_id"],
                invoice_id=d.get("invoice_id") or None,
                from_account_id=d.get("from_account_id") or None,
                to_account_id=d.get("to_account_id") or None,
                direction=d["direction"],
                payment_type=d.get("payment_type", "transfer"),
                currency=d["currency"],
                amount=Decimal(str(d["amount"])),
                rate_irr=int(d.get("rate_irr", 0)),
                date=d["date"],
                reference=d.get("reference", ""),
                note=d.get("note", ""),
                created_by=request.user,
            )
            return Response({
                "id": p.id,
                "amount_irr": p.amount_irr,
                "message": "پرداخت با موفقیت ثبت شد",
            }, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# ─── Reports ─────────────────────────────────────────────────

class BalanceReportView(APIView):
    """گزارش تراز — ریالی و ارزی"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        contacts = Contact.objects.filter(is_active=True)
        data = []
        for c in contacts:
            bal_irr = c.balance_irr
            bal_cny = float(c.balance_cny)
            if bal_irr != 0 or bal_cny != 0:
                data.append({
                    "id": c.id,
                    "name": c.name,
                    "contact_type_display": c.get_contact_type_display(),
                    "balance_irr": bal_irr,
                    "balance_cny": bal_cny,
                    "status_irr": "بدهکار" if bal_irr > 0 else "بستانکار",
                    "status_cny": "بدهکار" if bal_cny > 0 else "بستانکار",
                })
        return Response({"contacts": data})


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
                sale_item = SaleItem.objects.create(
                    invoice=inv,
                    variant_id=item_d['variant_id'],
                    quantity=int(item_d['quantity']),
                    unit_price=int(item_d['unit_price']),
                    discount_percent=item_d.get('discount_percent', 0),
                )
                # کم کردن موجودی از انبار
                try:
                    from apps.inventory.models import StockMovement, WarehouseStock
                    from apps.catalog.models import ProductVariant
                    qty = int(item_d['quantity'])
                    variant_id = int(item_d['variant_id'])
                    stock = WarehouseStock.objects.filter(
                        variant_id=variant_id,
                        warehouse__is_active=True,
                        quantity__gt=0
                    ).order_by('-quantity').first()
                    if stock:
                        StockMovement.record(
                            warehouse=stock.warehouse,
                            variant=stock.variant,
                            movement_type='sale',
                            quantity=-qty,
                            unit_price=int(item_d.get('unit_price', 0)),
                            reference=inv.invoice_number,
                            note=f'فاکتور فروش {inv.invoice_number}',
                            user=request.user,
                        )
                    else:
                        variant_obj = ProductVariant.objects.get(id=variant_id)
                        if variant_obj.stock_quantity >= qty:
                            variant_obj.stock_quantity -= qty
                            variant_obj.save(update_fields=['stock_quantity'])
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f'stock deduction failed: {e}')

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
        from django.db.models import Q, Value
        from django.db.models.functions import Concat
        q = request.query_params.get('q', '')
        if len(q) < 2:
            return Response([])
        users = User.objects.filter(
            Q(phone__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )[:15]
        data = []
        for u in users:
            full_name = f"{u.first_name} {u.last_name}".strip() or str(u)
            data.append({
                'id': u.id,
                'name': full_name,
                'phone': getattr(u, 'phone', ''),
                'display': f"{full_name} | {getattr(u, 'phone', '')}",
            })
        return Response(data)


class VariantPriceView(APIView):
    """GET /api/accounting/variant-price/<variant_id>/ — قیمت فروش کالا"""
    permission_classes = [IsAdminUser]

    def get(self, request, variant_id):
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
            return Response({'error': 'یافت نشد'}, status=404)


# ─── RBAC Views ──────────────────────────────────────────────

class RoleListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import Role, PERMISSIONS
        roles = Role.objects.all()
        return Response({
            'roles': [{
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'permissions': r.permissions,
                'perm_count': r.perm_count(),
                'staff_count': r.staff_members.filter(is_active=True).count(),
                'is_active': r.is_active,
            } for r in roles],
            'all_permissions': [{'code': k, 'label': v} for k, v in PERMISSIONS],
        })

    def post(self, request):
        from apps.users.models import Role
        d = request.data
        r = Role.objects.create(
            name=d['name'],
            description=d.get('description', ''),
            permissions=d.get('permissions', []),
        )
        return Response({'id': r.id, 'name': r.name}, status=201)


class RoleDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        from apps.users.models import Role
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        if 'name' in request.data:
            role.name = request.data['name']
        if 'description' in request.data:
            role.description = request.data['description']
        if 'permissions' in request.data:
            role.permissions = request.data['permissions']
        if 'is_active' in request.data:
            role.is_active = request.data['is_active']
        role.save()
        return Response({'id': role.id, 'name': role.name, 'permissions': role.permissions})

    def delete(self, request, pk):
        from apps.users.models import Role
        try:
            role = Role.objects.get(pk=pk)
            role.delete()
            return Response({'deleted': True})
        except Role.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)


class StaffListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import StaffProfile, Role
        staff = StaffProfile.objects.select_related('user', 'role').filter(is_active=True)
        return Response([{
            'id': s.id,
            'user_id': s.user_id,
            'name': s.user.get_full_name() or s.user.phone,
            'phone': s.user.phone,
            'role_id': s.role_id,
            'role_name': s.role.name if s.role else '',
            'employee_id': s.employee_id,
            'department': s.department,
            'is_active': s.is_active,
        } for s in staff])

    def post(self, request):
        from apps.users.models import StaffProfile, User
        d = request.data
        try:
            user = User.objects.get(id=d['user_id'])
            staff, created = StaffProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role_id': d.get('role_id') or None,
                    'employee_id': d.get('employee_id', ''),
                    'department': d.get('department', ''),
                }
            )
            if not created:
                if d.get('role_id'):
                    staff.role_id = d['role_id']
                staff.employee_id = d.get('employee_id', staff.employee_id)
                staff.department = d.get('department', staff.department)
                staff.is_active = True
                staff.save()
            # is_staff را فعال کن
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            return Response({'id': staff.id, 'message': 'پرسنل ثبت شد'}, status=201)
        except User.DoesNotExist:
            return Response({'error': 'کاربر یافت نشد'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class StaffDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        from apps.users.models import StaffProfile
        try:
            staff = StaffProfile.objects.get(pk=pk)
        except StaffProfile.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        if 'role_id' in request.data:
            staff.role_id = request.data['role_id'] or None
        if 'employee_id' in request.data:
            staff.employee_id = request.data['employee_id']
        if 'department' in request.data:
            staff.department = request.data['department']
        if 'is_active' in request.data:
            staff.is_active = request.data['is_active']
        staff.save()
        return Response({'id': staff.id})


class MyPermissionsView(APIView):
    """دسترسی‌های کاربر جاری"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        if request.user.is_superuser:
            from apps.users.models import PERMISSIONS
            return Response({
                'is_superuser': True,
                'permissions': [p[0] for p in PERMISSIONS],
            })
        try:
            staff = request.user.staff_profile
            return Response({
                'is_superuser': False,
                'role': staff.role.name if staff.role else '',
                'permissions': staff.role.permissions if staff.role else [],
            })
        except Exception:
            return Response({'permissions': [], 'role': ''})


class StaffCreateUserView(APIView):
    """POST /api/accounting/staff/create-user/ — ساخت کاربر جدید برای پرسنل"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        from apps.users.models import User
        d = request.data
        phone = d.get('phone', '').strip()
        password = d.get('password', '').strip()

        if not phone:
            return Response({'error': 'شماره موبایل الزامی است'}, status=400)
        if not password or len(password) < 6:
            return Response({'error': 'رمز عبور باید حداقل ۶ کاراکتر باشد'}, status=400)
        if User.objects.filter(phone=phone).exists():
            return Response({'error': 'این شماره موبایل قبلاً ثبت شده'}, status=400)

        try:
            user = User.objects.create_user(
                phone=phone,
                password=password,
                first_name=d.get('first_name', ''),
                last_name=d.get('last_name', ''),
                is_staff=True,
            )
            full_name = user.get_full_name() or phone
            return Response({
                'user_id': user.id,
                'name': full_name,
                'phone': phone,
                'message': f'کاربر {full_name} ساخته شد',
            }, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
