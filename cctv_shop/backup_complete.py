"""
python backup_complete.py
بک‌آپ کامل پروژه با نام complete
"""
import os, shutil, zipfile, datetime

BASE = os.path.join('..', 'cctv_project')
BACKUP_NAME = f'cctv_project_complete_{datetime.datetime.now().strftime("%Y%m%d_%H%M")}'
BACKUP_ZIP = BACKUP_NAME + '.zip'

EXCLUDE_DIRS = {
    '__pycache__', 'node_modules', '.git', 'venv',
    'dist', 'build', '.vite', 'migrations'
}
EXCLUDE_EXTS = {'.pyc', '.pyo', '.db-journal'}

print(f"📦 ساخت بک‌آپ: {BACKUP_ZIP}")

total_files = 0
with zipfile.ZipFile(BACKUP_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(BASE):
        # حذف دایرکتوری‌های استثنا
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if any(file.endswith(ext) for ext in EXCLUDE_EXTS):
                continue
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, os.path.dirname(BASE))
            try:
                zf.write(filepath, arcname)
                total_files += 1
            except Exception as e:
                print(f"  skip: {filepath} — {e}")

size_mb = os.path.getsize(BACKUP_ZIP) / (1024 * 1024)
print(f"✅ بک‌آپ کامل شد!")
print(f"   فایل‌ها: {total_files:,}")
print(f"   حجم: {size_mb:.1f} MB")
print(f"   نام: {BACKUP_ZIP}")
print(f"\nمسیر فایل بک‌آپ:")
print(f"  {os.path.abspath(BACKUP_ZIP)}")
