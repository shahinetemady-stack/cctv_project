from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from apps.orders.models import Order
from apps.users.models import User, UserProfile
from apps.catalog.models import ProductVariant


class DashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start  = today_start - timedelta(days=7)
        month_start = today_start.replace(day=1)
        paid_statuses = ["paid", "ready_to_ship", "shipped"]

        def sales(start):
            r = Order.objects.filter(status__in=paid_statuses, created_at__gte=start)\
                .aggregate(total=Sum("total_amount"))
            return int(r["total"] or 0)

        monthly = []
        for i in range(5, -1, -1):
            d = now - timedelta(days=30*i)
            m_start = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            m_end = now if i == 0 else (m_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            r = Order.objects.filter(
                status__in=paid_statuses,
                created_at__gte=m_start, created_at__lt=m_end
            ).aggregate(total=Sum("total_amount"), count=Count("id"))
            monthly.append({
                "month": str(m_start.date()),
                "total": int(r["total"] or 0),
                "count": r["count"] or 0,
            })

        # ─── آمار گسترده برای داشبورد مدیریت ─────────────────────
        from django.db.models import F
        from apps.orders.models import OrderItem

        # فروش روزانه ۳۰ روز اخیر
        daily = []
        for i in range(29, -1, -1):
            d0 = today_start - timedelta(days=i)
            d1 = d0 + timedelta(days=1)
            r = Order.objects.filter(
                status__in=paid_statuses, created_at__gte=d0, created_at__lt=d1
            ).aggregate(total=Sum("total_amount"), count=Count("id"))
            daily.append({"day": str(d0.date()), "total": int(r["total"] or 0), "count": r["count"]})

        # ماه قبل (برای درصد تغییر)
        prev_m_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_month_total = int(Order.objects.filter(
            status__in=paid_statuses, created_at__gte=prev_m_start, created_at__lt=month_start
        ).aggregate(t=Sum("total_amount"))["t"] or 0)

        # توزیع وضعیت سفارش‌ها
        orders_by_status = [
            {"status": s["status"], "count": s["c"]}
            for s in Order.objects.values("status").annotate(c=Count("id")).order_by("-c")
        ]

        # محصولات برتر بر اساس درآمد
        top_products = [{
            "name": t["variant__product__name"],
            "revenue": int(t["revenue"] or 0),
            "qty": t["qty"] or 0,
        } for t in (OrderItem.objects.filter(order__status__in=paid_statuses)
                    .values("variant__product__name")
                    .annotate(revenue=Sum(F("quantity") * F("unit_price")), qty=Sum("quantity"))
                    .order_by("-revenue")[:5])]

        # فروش بر اساس دسته‌بندی
        sales_by_category = [{
            "name": c["variant__product__category__name"] or "بدون دسته",
            "total": int(c["total"] or 0),
        } for c in (OrderItem.objects.filter(order__status__in=paid_statuses)
                    .values("variant__product__category__name")
                    .annotate(total=Sum(F("quantity") * F("unit_price")))
                    .order_by("-total"))]

        last_orders = []
        for o in Order.objects.select_related("user").order_by("-created_at")[:8]:
            last_orders.append({
                "order_number": o.order_number,
                "user": str(o.user.phone or "-"),
                "status": o.status,
                "amount": int(o.total_amount or 0),
                "created_at": o.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        return Response({
            "sales": {"today": sales(today_start), "week": sales(week_start), "month": sales(month_start)},
            "orders": {
                "today": Order.objects.filter(created_at__gte=today_start).count(),
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
        })
