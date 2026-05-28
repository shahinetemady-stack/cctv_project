import shutil, os

BASE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(BASE, '..', 'cctv_frontend', 'src')

files = [
    ('Header.jsx',        os.path.join(FRONTEND, 'components', 'layout', 'Header.jsx')),
    ('Layout.jsx',        os.path.join(FRONTEND, 'components', 'layout', 'Layout.jsx')),
    ('DashboardPage.jsx', os.path.join(FRONTEND, 'pages', 'admin', 'DashboardPage.jsx')),
]

for src, dst in files:
    if os.path.exists(src):
        shutil.copy(src, dst)
        print(f"✓ {src} → کپی شد")
    else:
        print(f"✗ {src} پیدا نشد — دانلود کنید و کنار این اسکریپت بگذارید")
