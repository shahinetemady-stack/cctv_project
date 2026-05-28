with open('apps/accounting/urls.py', 'w', encoding='utf-8') as f:
    f.write("""from django.urls import path
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
]
""")
print("done")
