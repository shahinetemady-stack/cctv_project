with open('apps/inventory/urls.py', 'w', encoding='utf-8') as f:
    f.write("""from django.urls import path
from . import views

urlpatterns = [
    path("stock/<int:variant_id>/", views.PublicStockView.as_view()),
    path("kardex/<int:variant_id>/", views.KardexView.as_view()),
    path("warehouses/", views.WarehouseSummaryView.as_view()),
    path("movements/", views.StockMovementCreateView.as_view()),
    path("admin-stock/<int:variant_id>/", views.AdminStockView.as_view()),
]
""")
print("done")
