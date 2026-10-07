from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
import jdatetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from apps.orders.models import Order
from apps.users.models import User, UserProfile
from apps.catalog.models import ProductVariant

J_MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
J_WEEKDAYS = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']  # jdatetime: شنبه=0

_FA_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')

def _fa(n):
    return str(n).translate(_FA_DIGITS)


class DashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "dashboard_view"):
            return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)

        from apps.accounting.models import SaleInvoice
        from apps.catalog.models import ExchangeRateSetting

        now = timezone.localtime()
        today = now.date()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # مرزهای ماه شمسی (نه میلادی) — به‌صورت تاریخ برای مقایسه با issue_date فاکتورها
        j_today = jdatetime.date.fromgregorian(date=today)
        month_start = jdatetime.date(j_today.year, j_today.month, 1).togregorian()
        j_prev = jdatetime.date(j_today.year, j_today.month, 1) - timedelta(days=1)
        prev_m_start = jdatetime.date(j_prev.year, j_prev.month, 1).togregorian()

        # ─── فروش واقعی فروشگاه = فاکتورهای فروش تأییدشده/تسویه‌شده ──────────
        # (سفارش‌های آنلاین سایت بعداً به فاکتور تبدیل می‌شوند؛ جدول Order مبنا نیست)
        from collections import defaultdict
        SALE_STATUSES = [SaleInvoice.Status.CONFIRMED, SaleInvoice.Status.PAID]
        rate = float(ExchangeRateSetting.get_instance().rate_cny_to_irt or 0)
        invoices = list(
            SaleInvoice.objects.filter(status__in=SALE_STATUSES)
            .prefetch_related('items__variant__product__category')
        )

        def inv_irr(inv):
            t = inv.total_amount
            return int(t * rate) if inv.currency == 'CNY' else int(t)

        def sales_since(d):
            return sum(inv_irr(i) for i in invoices if i.issue_date >= d)

        # فروش ۶ ماه شمسی اخیر
        monthly = []
        total_months = j_today.year * 12 + (j_today.month - 1)
        for k in range(total_months - 5, total_months + 1):
            jy, jm0 = divmod(k, 12)
            ny, nm0 = divmod(k + 1, 12)
            m_start = jdatetime.date(jy, jm0 + 1, 1).togregorian()
            m_end = None if k == total_months else jdatetime.date(ny, nm0 + 1, 1).togregorian()
            month_invs = [i for i in invoices
                          if i.issue_date >= m_start and (m_end is None or i.issue_date < m_end)]
            monthly.append({
                "month": str(m_start),
                "label": f"{J_MONTHS[jm0]} {_fa(jy)}",
                "total": sum(inv_irr(i) for i in month_invs),
                "count": len(month_invs),
            })

        # فروش روزانه ماه شمسی جاری (از ۱ ماه تا امروز)
        by_day_total = defaultdict(int)
        by_day_count = defaultdict(int)
        for i in invoices:
            by_day_total[i.issue_date] += inv_irr(i)
            by_day_count[i.issue_date] += 1
        daily = []
        d = month_start
        while d <= today:
            daily.append({"day": str(d), "total": by_day_total.get(d, 0), "count": by_day_count.get(d, 0)})
            d += timedelta(days=1)

        # ماه شمسی قبل (برای درصد تغییر)
        prev_month_total = sum(inv_irr(i) for i in invoices
                               if prev_m_start <= i.issue_date < month_start)

        # محصولات برتر و فروش دسته‌ای — از آیتم‌های فاکتورها
        prod_rev, prod_qty, cat_rev = defaultdict(int), defaultdict(int), defaultdict(int)
        for inv in invoices:
            factor = rate if inv.currency == 'CNY' else 1
            for it in inv.items.all():
                sub_irr = int(it.subtotal * factor)
                product = it.variant.product
                prod_rev[product.name] += sub_irr
                prod_qty[product.name] += it.quantity
                cat_rev[product.category.name if product.category else "بدون دسته"] += sub_irr
        top_products = [
            {"name": name, "revenue": rev, "qty": prod_qty[name]}
            for name, rev in sorted(prod_rev.items(), key=lambda kv: -kv[1])[:5]
        ]
        sales_by_category = [
            {"name": name, "total": total}
            for name, total in sorted(cat_rev.items(), key=lambda kv: -kv[1])
        ]

        # توزیع وضعیت — سفارش‌های سایت + فاکتورها
        status_counts = defaultdict(int)
        for s in Order.objects.values("status").annotate(c=Count("id")):
            status_counts[s["status"]] += s["c"]
        for s in SaleInvoice.objects.values("status").annotate(c=Count("id")):
            status_counts[s["status"]] += s["c"]
        orders_by_status = [
            {"status": st, "count": c}
            for st, c in sorted(status_counts.items(), key=lambda kv: -kv[1])
        ]

        # آخرین سفارش‌های سایت + آخرین فاکتورها (مرتب بر اساس تاریخ)
        # نام مشتری: نام کامل حساب → نام طرف حساب لینک‌شده → موبایل
        def _order_customer_name(o):
            name = o.user.get_full_name()
            if name:
                return name
            prof = getattr(o.user, "profile", None)
            if prof and prof.linked_contact_id:
                return prof.linked_contact.name
            return str(o.user.phone or "-")

        last_items = [
            (o.created_at, {
                "order_number": o.order_number,
                "user": _order_customer_name(o),
                "status": o.status,
                "amount": int(o.total_amount or 0),
            })
            for o in Order.objects.select_related("user", "user__profile", "user__profile__linked_contact").order_by("-created_at")[:8]
        ]
        last_items += [
            (i.created_at, {
                "order_number": i.invoice_number,
                "user": i.customer_name or (i.customer_phone or "-"),
                "status": i.status,
                "amount": inv_irr(i),
            })
            for i in SaleInvoice.objects.order_by("-created_at")[:8]
        ]
        last_items.sort(key=lambda x: x[0], reverse=True)
        last_orders = [
            {**payload, "created_at": timezone.localtime(dt).strftime("%Y-%m-%d %H:%M")}
            for dt, payload in last_items[:8]
        ]

        # هشدار انقضای سرویس‌ها (دامنه/سرور/…) — فقط برای سوپریوزر (اطلاعات حساس)
        expiring_services = []
        if request.user.is_superuser:
            from apps.core.models import ServiceSubscription
            expiring_services = [
                {
                    "id": s.id,
                    "name": s.name,
                    "category_display": s.get_category_display(),
                    "provider": s.provider,
                    "expire_date": s.expire_date.isoformat(),
                    "days_left": s.days_left,
                    "auto_renew": s.auto_renew,
                }
                for s in ServiceSubscription.objects.filter(is_active=True)
                if s.days_left <= s.warn_days
            ]

        return Response({
            "sales": {
                "today": sales_since(today),
                "week": sales_since(today - timedelta(days=7)),
                "month": sales_since(month_start),
            },
            "orders": {
                "today": Order.objects.filter(created_at__gte=today_start).count()
                         + SaleInvoice.objects.filter(issue_date=today).count(),
                "pending": Order.objects.filter(status="pending").count(),
                "awaiting_payment": Order.objects.filter(status="awaiting_payment").count(),
            },
            "users": {
                "new_today": User.objects.filter(date_joined__gte=today_start).count(),
                "partner_requests": UserProfile.objects.filter(user_type="partner", is_approved=False).count(),
            },
            "inventory": {
                "low_stock": ProductVariant.objects.filter(is_active=True, stock_quantity__lte=5, stock_quantity__gt=0).count(),
                "out_of_stock": ProductVariant.objects.filter(is_active=True, stock_quantity=0).count(),
            },
            "monthly_sales": monthly,
            "last_orders": last_orders,
            "daily_sales": daily,
            "prev_month_sales": prev_month_total,
            "orders_by_status": orders_by_status,
            "top_products": top_products,
            "sales_by_category": sales_by_category,
            "month_label": J_MONTHS[j_today.month - 1],
            "today_label": f"{J_WEEKDAYS[j_today.weekday()]} {_fa(j_today.day)} {J_MONTHS[j_today.month - 1]} {_fa(j_today.year)}",
            "expiring_services": expiring_services,
        })
