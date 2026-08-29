from django.urls import path
from . import views

urlpatterns = [
    path("stock/<int:variant_id>/", views.PublicStockView.as_view()),
    path("kardex/<int:variant_id>/", views.KardexView.as_view()),
    path("warehouses/", views.WarehouseSummaryView.as_view()),
    path("warehouses/<int:pk>/", views.WarehouseDetailView.as_view()),
    path("warehouses/<int:pk>/stocks/", views.WarehouseStockListView.as_view()),
    path("transfers/", views.TransferListCreateView.as_view()),
    path("movements/", views.StockMovementCreateView.as_view()),
    path("admin-stock/<int:variant_id>/", views.AdminStockView.as_view()),
]
