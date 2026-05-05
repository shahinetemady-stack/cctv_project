"""
python fix_urls.py
"""
import os

print("اصلاح catalog/urls.py ...")

urls_content = """from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/search/", views.ProductSearchView.as_view(), name="product-search"),
    path("products/bulk-upload/", views.bulk_upload_products, name="product-bulk-upload"),
    path("products/<str:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("exchange-rate/", views.ExchangeRateView.as_view(), name="exchange-rate"),
]
"""

with open(os.path.join('apps', 'catalog', 'urls.py'), 'w', encoding='utf-8') as f:
    f.write(urls_content)

print("OK - slug:slug به str:slug تغییر کرد")
print()
print("حالا سرور را restart کنید:")
print("Ctrl+C بزنید و دوباره: python manage.py runserver")
