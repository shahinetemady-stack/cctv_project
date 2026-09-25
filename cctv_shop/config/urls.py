from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import home_view, social_meta_view, llms_txt_view
from apps.catalog.legacy_redirects import (
    legacy_blog_redirect,
    legacy_category_redirect,
    legacy_product_redirect,
)
from django.contrib.sitemaps.views import sitemap as sitemap_view
from config.sitemaps import sitemaps
from apps.catalog.views import TorobProductsV3View

urlpatterns = [
    # ریدایرکت ۳۰۱ از URLهای سایت قدیمی doorbinkar.com
    re_path(r"^cat/(?P<legacy_id>\d+)(?:/(?P<rest>.*))?$", legacy_category_redirect),
    re_path(r"^products/(?P<legacy_id>\d+)(?:/(?P<rest>.*))?$", legacy_product_redirect),
    re_path(r"^blog/(?P<legacy_id>\d+)(?:/(?P<rest>.*))?$", legacy_blog_redirect),
    # OG برای کرولرهای پیش‌نمایش لینک — nginx فقط UA ربات‌های اجتماعی را اینجا می‌آورد.
    # اسلاگ‌ها فارسی‌اند، پس به‌جای <slug:> از regex [^/]+ استفاده می‌شود.
    re_path(r"^(?P<kind>products|categories|packages|blog|videos)/(?P<slug>[^/]+)/$", social_meta_view),
    path("sitemap.xml", sitemap_view, {"sitemaps": sitemaps}, name="sitemap"),
    path("llms.txt", llms_txt_view, name="llms-txt"),
    path("", home_view, name="home"),
    path("torob_api/v3/products", TorobProductsV3View.as_view(), name="torob-products-v3"),
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
    path("api/assistant/", include("apps.assistant.urls")),
    path("api/payroll/", include("apps.payroll.urls")),
    path("api/expenses/", include("apps.expenses.urls")),
    path("api/leads/", include("apps.leads.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
