import os

app_path = os.path.join('..', 'cctv_frontend', 'src', 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'SaleInvoicePage' not in app:
    app = app.replace(
        "import ReportsPage",
        "import SaleInvoicePage from './pages/admin/SaleInvoicePage'\nimport FinancialReportsPage from './pages/admin/FinancialReportsPage'\nimport ReportsPage"
    )
    app = app.replace(
        '<Route path="admin/reports"',
        '<Route path="admin/sales" element={<RequireAuth><SaleInvoicePage /></RequireAuth>} />\n        <Route path="admin/financial" element={<RequireAuth><FinancialReportsPage /></RequireAuth>} />\n        <Route path="admin/reports"'
    )
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("App.jsx updated")
else:
    print("Already updated")
