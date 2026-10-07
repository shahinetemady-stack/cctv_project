from django.urls import path

from . import views

urlpatterns = [
    path("recipes/", views.RecipeListView.as_view(), name="production-recipes"),
    path("recipes/<int:pk>/", views.RecipeDetailView.as_view(), name="production-recipe-detail"),
    path("orders/", views.OrderListView.as_view(), name="production-orders"),
    path("orders/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="production-order-cancel"),
]
