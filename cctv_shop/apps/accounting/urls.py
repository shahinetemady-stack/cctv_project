"""apps/accounting/urls.py"""
from django.urls import path
from . import views
from .admin_tools import SystemResetPageView
from .backup_tools import (
    BackupPageView, BackupRestorePageView, BrowseDirectoryView,
    # JSON API for frontend
    BackupSettingsApiView, BackupRunApiView, BackupLogsApiView,
    BrowseDirectoryApiView, BackupRestoreUploadApiView, BackupRestoreExecuteApiView,
    SystemResetApiView,
)

urlpatterns = [
    path("accounts/", views.AccountListView.as_view(), name="accounts"),
    path("accounts/<int:pk>/", views.AccountDetailView.as_view(), name="account-detail"),
    path("accounts/<int:pk>/transactions/", views.AccountTransactionsView.as_view(), name="account-transactions"),
    path("contacts/", views.ContactListView.as_view(), name="contacts"),
    path("contacts/<pk>/", views.ContactDetailView.as_view(), name="contact-detail"),
    path("contacts/<pk>/activate-user/", views.ContactUserActivationView.as_view(), name="contact-activate-user"),
    path("my/dashboard/", views.MyDashboardView.as_view(), name="my-dashboard"),
    path("my/kardex/", views.MyKardexView.as_view(), name="my-kardex"),

    path("purchase-invoices/", views.PurchaseInvoiceListView.as_view(), name="purchase-invoices"),
    path("purchase-invoices/last-price/", views.PurchaseLastPriceView.as_view(), name="purchase-last-price"),
    path("purchase-invoices/pending-receive/", views.PurchaseInvoicePendingReceiveView.as_view(), name="purchase-pending-receive"),
    path("purchase-invoices/<int:pk>/", views.PurchaseInvoiceDetailView.as_view(), name="purchase-detail"),
    path("purchase-invoices/<int:pk>/receive/", views.PurchaseInvoiceReceiveView.as_view(), name="purchase-receive"),

    path("payments/", views.PaymentListView.as_view(), name="payments"),
    path("payments/voucher/", views.PaymentVoucherView.as_view(), name="payment-voucher"),
    path("payments/internal-transfer/", views.PaymentInternalTransferView.as_view(), name="payment-internal-transfer"),
    path("payments/<int:pk>/reverse/", views.PaymentReverseView.as_view(), name="payment-reverse"),
    path("cheques/", views.ChequeListView.as_view(), name="cheques"),
    path("cheques/available/", views.ChequeAvailableView.as_view(), name="cheques-available"),
    path("cheques/<int:pk>/", views.ChequeDetailView.as_view(), name="cheque-detail"),
    path("cheques/<int:pk>/action/", views.ChequeActionView.as_view(), name="cheque-action"),
    path("payments/<int:pk>/", views.PaymentDetailView.as_view(), name="payment-detail"),

    path("returns/", views.ReturnInvoiceListView.as_view(), name="returns"),
    path("returns/<int:pk>/", views.ReturnInvoiceDetailView.as_view(), name="return-detail"),
    path("returns/<int:pk>/cancel/", views.ReturnInvoiceCancelView.as_view(), name="return-cancel"),
    path("reports/balance/", views.BalanceReportView.as_view(), name="balance-report"),
    path("reports/sales-channels/", views.SalesChannelReportView.as_view(), name="sales-channels-report"),
    path("reports/aging/", views.AgingReportView.as_view(), name="aging-report"),
    path("reports/profit/", views.ProfitReportView.as_view(), name="profit-report"),
    path("reports/balance-sheet/", views.BalanceSheetView.as_view(), name="balance-sheet"),

    path("sale-invoices/last-price/", views.SaleLastPriceView.as_view(), name="sale-last-price"),
    path("sale-invoices/", views.SaleInvoiceListView.as_view(), name="sale-invoices"),
    path("sale-invoices/<int:pk>/", views.SaleInvoiceDetailView.as_view(), name="sale-invoice-detail"),
    path("sale-invoices/<int:pk>/void/", views.SaleInvoiceVoidView.as_view(), name="sale-invoice-void"),
    path("sale-invoices/<int:pk>/send-account-info/", views.SaleInvoiceSendAccountInfoView.as_view(), name="sale-invoice-send-account-info"),
    path("sale-payments/", views.SalePaymentCreateView.as_view(), name="sale-payments"),
    path("sale-payments/<int:pk>/", views.SalePaymentDetailView.as_view(), name="sale-payment-detail"),

    path("pending-orders/", views.PendingOrdersView.as_view(), name="pending-orders"),
    path("customer-search/", views.CustomerSearchView.as_view(), name="customer-search"),
    path("customers/", views.CustomerQuickCreateView.as_view(), name="customer-quick-create"),
    path("variant-price/<int:variant_id>/", views.VariantPriceView.as_view(), name="variant-price"),

    path("roles/", views.RoleListView.as_view(), name="roles"),
    path("roles/<int:pk>/", views.RoleDetailView.as_view(), name="role-detail"),
    path("staff/", views.StaffListView.as_view(), name="staff"),
    path("staff/<int:pk>/", views.StaffDetailView.as_view(), name="staff-detail"),
    path("staff/create-user/", views.StaffCreateUserView.as_view(), name="staff-create-user"),
    path("my-permissions/", views.MyPermissionsView.as_view(), name="my-permissions"),

    # Django admin HTML pages
    path("system-reset-page/", SystemResetPageView.as_view(), name="system-reset-page"),
    path("backup-page/", BackupPageView.as_view(), name="backup-page"),
    path("backup-restore-page/", BackupRestorePageView.as_view(), name="backup-restore-page"),
    path("browse-directory/", BrowseDirectoryView.as_view(), name="browse-directory"),

    # JSON API for React frontend
    path("backup/settings/", BackupSettingsApiView.as_view(), name="backup-api-settings"),
    path("backup/run/", BackupRunApiView.as_view(), name="backup-api-run"),
    path("backup/logs/", BackupLogsApiView.as_view(), name="backup-api-logs"),
    path("backup/browse/", BrowseDirectoryApiView.as_view(), name="backup-api-browse"),
    path("backup/restore/upload/", BackupRestoreUploadApiView.as_view(), name="backup-api-restore-upload"),
    path("backup/restore/execute/", BackupRestoreExecuteApiView.as_view(), name="backup-api-restore-execute"),
    path("system-reset/", SystemResetApiView.as_view(), name="system-reset-api"),
]
