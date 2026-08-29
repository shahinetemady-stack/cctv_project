"""
دستور run_daily_backup — برای Windows Task Scheduler

استفاده هر شب آخر شب (مثلا 23:30):
  python manage.py run_daily_backup

تفاوت با run_backup: این بک‌اپ روزانه است که با retention جدا نگه‌داری می‌شود
(پیش‌فرض 30 روز).
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "اجرای بک‌اپ روزانه — برای Task Scheduler"

    def handle(self, *args, **options):
        from apps.accounting.backup_tools import run_backup, BackupLog, BackupSetting

        s = BackupSetting.get_instance()
        if not s.daily_backup_enabled:
            self.stdout.write(self.style.WARNING("بک‌اپ روزانه غیرفعال است"))
            return

        self.stdout.write("شروع بک‌اپ روزانه...")
        log = run_backup(trigger=BackupLog.Trigger.DAILY, is_daily=True)

        if log.status == BackupLog.Status.SUCCESS:
            self.stdout.write(self.style.SUCCESS(
                f"✓ بک‌اپ روزانه — {log.file_size_mb}MB در {log.duration_seconds}s"
            ))
        elif log.status == BackupLog.Status.PARTIAL:
            self.stdout.write(self.style.WARNING(f"⚠ {log.error}"))
        else:
            self.stdout.write(self.style.ERROR(f"✗ {log.error}"))
