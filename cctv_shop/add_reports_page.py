"""
python add_reports_page.py
اضافه کردن ReportsPage به App.jsx
اجرا در پوشه cctv_shop
"""
import os, shutil

FRONTEND_SRC = os.path.join("..", "cctv_frontend", "src")
pages_admin = os.path.join(FRONTEND_SRC, "pages", "admin")

# کپی ReportsPage.jsx
src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cctv_frontend", "src", "pages", "admin")
# فایل را از همین پوشه بگیر
reports_src = "ReportsPage.jsx"  # باید کنار این فایل باشد
reports_dst = os.path.join(pages_admin, "ReportsPage.jsx")

# محتوای ReportsPage
content = open(reports_src, encoding="utf-8").read()
with open(reports_dst, "w", encoding="utf-8") as f:
    f.write(content)
print(f"✓ ReportsPage.jsx کپی شد")

# آپدیت App.jsx
app_path = os.path.join(FRONTEND_SRC, "App.jsx")
with open(app_path, encoding="utf-8") as f:
    app = f.read()

if "ReportsPage" not in app:
    app = app.replace(
        "import KardexPage",
        "import ReportsPage from './pages/admin/ReportsPage'\nimport KardexPage"
    )
    app = app.replace(
        '<Route path="admin/kardex"',
        '<Route path="admin/reports" element={<RequireAuth><ReportsPage /></RequireAuth>} />\n        <Route path="admin/kardex"'
    )
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(app)
    print("✓ App.jsx آپدیت شد")
    print("آدرس جدید: /admin/reports")
else:
    print("✓ ReportsPage قبلاً در App.jsx بود")
