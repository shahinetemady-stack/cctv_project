"""
دستور run_backup — اجرای بک‌اپ از طریق command line / Task Scheduler

استفاده:
  python manage.py run_backup
  python manage.py run_backup --trigger auto

برای Windows Task Scheduler:
  Program: C:\path\to\venv\Scripts\python.exe
  Arguments: manage.py run_backup --trigger auto
  Start in: C:\path\to\cctv_shop
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "اجرای بک‌اپ سیستم — برای استفاده با Task Scheduler"

    def add_arguments(self, parser):
        parser.add_argument(
            "--trigger",
            choices=['command', 'auto'],
            default='command',
            help="منبع اجرا (command یا auto)",
        )

    def handle(self, *args, **options):
        from apps.accounting.backup_tools import run_backup, BackupLog

        trigger = options['trigger']
        self.stdout.write(f"شروع بک‌اپ ({trigger})...")

        log = run_backup(trigger=trigger)

        if log.status == BackupLog.Status.SUCCESS:
            self.stdout.write(self.style.SUCCESS(
                f"✓ موفق — {log.file_size_mb}MB در {log.duration_seconds}s"
            ))
            if log.sent_email:
                self.stdout.write("  ✓ ارسال به ایمیل")
            if log.sent_telegram:
                self.stdout.write("  ✓ ارسال به تلگرام")
            if log.file_path:
                self.stdout.write(f"  📁 {log.file_path}")
        elif log.status == BackupLog.Status.PARTIAL:
            self.stdout.write(self.style.WARNING(f"⚠ نسبتاً موفق — {log.error}"))
        else:
            self.stdout.write(self.style.ERROR(f"✗ خطا: {log.error}"))
