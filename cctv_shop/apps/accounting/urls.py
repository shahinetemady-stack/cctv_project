from django.urls import path
from . import views

urlpatterns = [
    path('accounts/', views.AccountListView.as_view()),
    path('contacts/', views.ContactListView.as_view()),
    path('contacts/<int:pk>/', views.ContactDetailView.as_view()),
    path('invoices/', views.PurchaseInvoiceListView.as_view()),
    path('invoices/<int:pk>/', views.PurchaseInvoiceDetailView.as_view()),
    path('payments/', views.PaymentCreateView.as_view()),
    path('reports/balance/', views.BalanceReportView.as_view()),
    path('sale-invoices/', views.SaleInvoiceListView.as_view()),
    path('sale-invoices/<int:pk>/', views.SaleInvoiceDetailView.as_view()),
    path('sale-payments/', views.SalePaymentCreateView.as_view()),
    path('pending-orders/', views.PendingOrdersView.as_view()),
    path('reports/profit/', views.ProfitReportView.as_view()),
    path('reports/balance-sheet/', views.BalanceSheetView.as_view()),
    path('customers/search/', views.CustomerSearchView.as_view()),
    path('variant-price/<int:variant_id>/', views.VariantPriceView.as_view()),
    path('roles/', views.RoleListView.as_view()),
    path('roles/<int:pk>/', views.RoleDetailView.as_view()),
    path('staff/', views.StaffListView.as_view()),
    path('staff/<int:pk>/', views.StaffDetailView.as_view()),
    path('staff/create-user/', views.StaffCreateUserView.as_view()),
    path('my-permissions/', views.MyPermissionsView.as_view()),
]
