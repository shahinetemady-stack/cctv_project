with open('config/urls.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/accounting/", include("apps.accounting.urls")),
    path("api/core/", include("apps.core.urls")),
    path("api/education/", include("apps.education.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/payment/", include("apps.payment.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
""")
print("✓ done")
