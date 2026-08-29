from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # Cart
    path("cart/",          views.CartView.as_view(),   name="cart"),
    path("cart/checkout/", views.cart_checkout,        name="cart-checkout"),
    # InquiryCart
    path("inquiry-cart/",        views.InquiryCartView.as_view(), name="inquiry-cart"),
    path("inquiry-cart/submit/", views.inquiry_cart_submit,       name="inquiry-cart-submit"),
    # Admin — مسیرهای ثابت باید قبل از پارامتری باشند تا قورت داده نشوند
    path("admin/orders/",                          views.AdminOrderListView.as_view()),
    path("admin/reject-report/",                   views.AdminRejectReportView.as_view()),
    path("admin/receipts/",                        views.AdminReceiptListCreateView.as_view()),
    path("admin/receipts/<int:pk>/approve/",       views.AdminReceiptApproveView.as_view()),
    path("admin/receipts/<int:pk>/reject/",        views.AdminReceiptRejectView.as_view()),
    path("admin/shortage-report/",                 views.AdminShortageReportView.as_view()),
    # Admin — پارامتری
    path("admin/<str:order_number>/",              views.AdminOrderDeleteView.as_view()),
    path("admin/<str:order_number>/reject/",       views.AdminOrderRejectView.as_view()),
    path("admin/<str:order_number>/confirm/",      views.admin_confirm_inquiry),
    path("admin/<str:order_number>/detail/",       views.AdminOrderDetailView.as_view()),
    path("admin/<str:order_number>/items/<int:item_id>/", views.AdminOrderItemUpdateView.as_view()),
    path("admin/<str:order_number>/update/",       views.AdminOrderUpdateView.as_view()),
    # Receipts (فیش واریزی)
    path("my-receipts/",                           views.MyReceiptsView.as_view()),
    path("my-overdue/",                            views.MyOverdueView.as_view()),
    # China
    path("china-request/",                         views.ChinaOrderRequestView.as_view()),
    # Orders — باید بعد از admin باشد
    path("",                                       views.OrderListView.as_view(),   name="order-list"),
    path("<str:order_number>/receipts/",           views.OrderReceiptCreateView.as_view()),
    path("<str:order_number>/",                    views.OrderDetailView.as_view(), name="order-detail"),
    path("<str:order_number>/cancel/",             views.cancel_order_view,         name="order-cancel"),
    path("<str:order_number>/track/",              views.OrderTrackingView.as_view()),
]
