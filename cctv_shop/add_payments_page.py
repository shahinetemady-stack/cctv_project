import os, shutil

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# کپی PaymentsPage
shutil.copy('PaymentsPage.jsx', os.path.join(FRONTEND, 'pages', 'admin', 'PaymentsPage.jsx'))
print("✓ PaymentsPage.jsx کپی شد")

# آپدیت App.jsx
app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'PaymentsPage' not in app:
    app = app.replace(
        "import FinancialReportsPage",
        "import PaymentsPage from './pages/admin/PaymentsPage'\nimport FinancialReportsPage"
    )
    app = app.replace(
        '<Route path="admin/financial"',
        '<Route path="admin/payments" element={<RequireAuth><PaymentsPage /></RequireAuth>} />\n        <Route path="admin/financial"'
    )
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("✓ App.jsx آپدیت شد")

# آپدیت Layout.jsx — تغییر مسیر دریافت/پرداخت و عنوان گزارش مالی
layout_path = os.path.join(FRONTEND, 'components', 'layout', 'Layout.jsx')
with open(layout_path, encoding='utf-8') as f:
    layout = f.read()

layout = layout.replace(
    "{ label: 'دریافت و پرداخت', path: '/admin/financial', perm: 'reports_view',  icon: '💰' }",
    "{ label: 'دریافت و پرداخت', path: '/admin/payments', perm: 'reports_view',  icon: '💰' },\n  { label: 'گزارش مالی پیشرفته', path: '/admin/financial', perm: 'reports_view', icon: '📈' }"
)

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(layout)
print("✓ Layout.jsx آپدیت شد")
print("\nفرانت‌اند را restart کنید")
