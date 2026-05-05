from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # Cart (مشتری عمومی)
    path("cart/",          views.CartView.as_view(),  name="cart"),
    path("cart/checkout/", views.cart_checkout,       name="cart-checkout"),
    # InquiryCart (مشتری همکار)
    path("inquiry-cart/",        views.InquiryCartView.as_view(), name="inquiry-cart"),
    path("inquiry-cart/submit/", views.inquiry_cart_submit,       name="inquiry-cart-submit"),
    # Orders (کاربر)
    path("",                          views.OrderListView.as_view(),   name="order-list"),
    path("<str:order_number>/",       views.OrderDetailView.as_view(), name="order-detail"),
    path("<str:order_number>/cancel/",views.cancel_order_view,         name="order-cancel"),
    # Admin
    path("admin/orders/",                       views.AdminOrderListView.as_view(),  name="admin-order-list"),
    path("admin/<str:order_number>/confirm/",   views.admin_confirm_inquiry,         name="admin-confirm-inquiry"),
]
