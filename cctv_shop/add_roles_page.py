import os, shutil

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

shutil.copy('RolesPage.jsx', os.path.join(FRONTEND, 'pages', 'admin', 'RolesPage.jsx'))
print("✓ RolesPage.jsx کپی شد")

app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'RolesPage' not in app:
    app = app.replace(
        "import ReportsPage",
        "import RolesPage from './pages/admin/RolesPage'\nimport ReportsPage"
    )
    app = app.replace(
        '<Route path="admin/reports"',
        '<Route path="admin/roles" element={<RequireAuth><RolesPage /></RequireAuth>} />\n        <Route path="admin/reports"'
    )
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("✓ App.jsx آپدیت شد")
    print("آدرس: /admin/roles")
