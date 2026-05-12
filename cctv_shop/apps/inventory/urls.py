from django.urls import path
from .views import PublicStockView, KardexView, WarehouseSummaryView
urlpatterns = [
    path("stock/<int:variant_id>/", PublicStockView.as_view()),
    path("kardex/<int:variant_id>/", KardexView.as_view()),
    path("warehouses/", WarehouseSummaryView.as_view()),
]
