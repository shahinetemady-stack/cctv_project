"""
python manage.py import_products --file products.xlsx
"""
import os
from django.core.management.base import BaseCommand
from apps.catalog.excel_importer import import_products_from_excel


class Command(BaseCommand):
    help = "وارد کردن محصولات از فایل Excel"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="مسیر فایل Excel")
        parser.add_argument("--dry-run", action="store_true", help="فقط نمایش بدون ذخیره")

    def handle(self, *args, **options):
        path = options["file"]
        if not os.path.exists(path):
            self.stderr.write(f"فایل یافت نشد: {path}")
            return

        results = import_products_from_excel(path, dry_run=options["dry_run"])
        self.stdout.write(f"\n✓ اضافه: {results['created']}")
        self.stdout.write(f"✓ بروزرسانی: {results['updated']}")
        if results["errors"]:
            self.stdout.write(f"✗ خطا: {len(results['errors'])}")
            for e in results["errors"][:5]:
                self.stdout.write(f"  - {e}")
