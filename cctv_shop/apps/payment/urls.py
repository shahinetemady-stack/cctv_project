from django.urls import path
from . import views

app_name = "payment"

urlpatterns = [
    # درگاه بانک
    path("bank/request/",          views.PaymentRequestView.as_view(),      name="bank-request"),
    path("bank/verify/",           views.PaymentCallbackView.as_view(),     name="bank-verify"),
    # وضعیت پرداخت
    path("status/<str:order_number>/", views.PaymentStatusView.as_view(),   name="payment-status"),
    # تراکنش‌های من
    path("transactions/",          views.TransactionListView.as_view(),     name="transaction-list"),
    # ادمین
    path("admin/transactions/",    views.AdminTransactionListView.as_view(),name="admin-transactions"),
]
