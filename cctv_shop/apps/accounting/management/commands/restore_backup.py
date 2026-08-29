"""
دستور restore_backup — بازیابی اطلاعات از فایل ZIP

استفاده:
  python manage.py restore_backup "C:\\path\\to\\backup.zip"

پارامترهای اختیاری:
  --no-db     فقط media را بازیابی کن، dbرا دست نزن
  --no-media  فقط db را بازیابی کن، media را دست نزن
  --no-safety  قبل از restore یک safety backup نگیر (به طور پیش‌فرض می‌گیرد)

⚠️ مهم: قبل از این دستور، سرور Django را stop کنید (Ctrl+C در runserver)
"""
import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "بازیابی اطلاعات از فایل ZIP بک‌اپ"

    def add_arguments(self, parser):
        parser.add_argument('zip_path', type=str, help="مسیر فایل ZIP بک‌اپ")
        parser.add_argument('--no-db', action='store_true', help="دیتابیس را بازیابی نکن")
        parser.add_argument('--no-media', action='store_true', help="media را بازیابی نکن")
        parser.add_argument('--no-safety', action='store_true', help="safety backup نگیر")
        parser.add_argument('--confirm', action='store_true', help="بدون پرسش")

    def handle(self, *args, **options):
        zip_path = options['zip_path']

        if not os.path.exists(zip_path):
            self.stdout.write(self.style.ERROR(f"فایل پیدا نشد: {zip_path}"))
            return

        self.stdout.write(self.style.WARNING("━" * 60))
        self.stdout.write(self.style.WARNING("⚠️  بازیابی اطلاعات از بک‌اپ"))
        self.stdout.write(self.style.WARNING("━" * 60))
        self.stdout.write(f"فایل: {zip_path}")
        self.stdout.write(f"اندازه: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")
        self.stdout.write(f"دیتابیس: {'نه' if options['no_db'] else 'بله'}")
        self.stdout.write(f"Media: {'نه' if options['no_media'] else 'بله'}")
        self.stdout.write("")

        if not options['confirm']:
            answer = input("برای ادامه تایپ کنید: RESTORE\n> ")
            if answer.strip() != "RESTORE":
                self.stdout.write(self.style.ERROR("لغو شد."))
                return

        # Safety backup
        if not options['no_safety']:
            try:
                from apps.accounting.backup_tools import safety_backup_now
                self.stdout.write("گرفتن safety backup...")
                safety_log = safety_backup_now(reason="قبل از restore")
                if safety_log:
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ safety backup: {safety_log.file_path}"
                    ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ⚠ safety backup ناموفق: {e}"))

        # Restore
        try:
            from apps.accounting.backup_tools import extract_backup_zip
            self.stdout.write("شروع بازیابی...")
            result = extract_backup_zip(zip_path,
                restore_db=not options['no_db'],
                restore_media=not options['no_media'])

            if result['db_restored']:
                self.stdout.write(self.style.SUCCESS("  ✓ دیتابیس بازیابی شد"))
            if result['media_restored']:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ {result['media_restored']} فایل media بازیابی شد"
                ))
            if result['errors']:
                self.stdout.write(self.style.WARNING(f"  ⚠ {len(result['errors'])} خطا"))

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("✅ بازیابی کامل شد"))
            self.stdout.write(self.style.WARNING("⚠️  سرور را restart کنید: python manage.py runserver"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا: {e}"))
            import traceback
            traceback.print_exc()
