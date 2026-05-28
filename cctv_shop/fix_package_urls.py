with open('apps/catalog/urls.py', 'w', encoding='utf-8') as f:
    f.write("""from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/search/", views.ProductSearchView.as_view(), name="product-search"),
    path("products/bulk-upload/", views.bulk_upload_products, name="product-bulk-upload"),
    path("products/<str:slug>/similar/", views.SimilarProductsView.as_view(), name="product-similar"),
    path("products/<str:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("packages/", views.PackageListView.as_view(), name="package-list"),
    path("packages/<str:slug>/", views.PackageDetailView.as_view(), name="package-detail"),
    path("exchange-rate/", views.ExchangeRateView.as_view(), name="exchange-rate"),
    path("variants/", views.VariantListView.as_view(), name="variant-list"),
]
""")
print("done")
