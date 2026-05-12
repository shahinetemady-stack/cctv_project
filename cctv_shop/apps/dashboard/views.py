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
                "month": f"{m_start.month}/{m_start.year}",
                "total": int(r["total"] or 0),
                "count": r["count"] or 0,
            })

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
        })
