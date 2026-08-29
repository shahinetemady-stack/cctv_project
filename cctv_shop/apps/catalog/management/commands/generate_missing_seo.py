"""
apps/catalog/management/commands/generate_missing_seo.py
──────────────────────────────────────────────────────────
Management command برای تولید خودکار فیلدهای SEO برای محصولات قدیمی.

استفاده:
  python manage.py generate_missing_seo            ← فقط فیلدهای خالی
  python manage.py generate_missing_seo --force    ← بازنویسی همه
  python manage.py generate_missing_seo --dry-run  ← فقط نمایش، بدون ذخیره
  python manage.py generate_missing_seo --id 5     ← فقط یک محصول
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "تولید خودکار فیلدهای SEO برای محصولات"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help="بازنویسی همه فیلدها حتی اگر پر باشند",
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="فقط نمایش — بدون ذخیره در دیتابیس",
        )
        parser.add_argument(
            '--id', type=int, default=None,
            help="فقط برای یک محصول خاص (شناسه عددی)",
        )

    def handle(self, *args, **options):
        from apps.catalog.models import Product
        from apps.catalog.seo import generate_all_seo_fields

        force   = options['force']
        dry_run = options['dry_run']
        prod_id = options['id']

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'[DRY RUN] ' if dry_run else ''}"
            f"تولید خودکار SEO {'(بازنویسی کامل)' if force else '(فقط فیلدهای خالی)'}"
        ))

        # فیلتر محصولات
        qs = Product.objects.filter(is_active=True)
        if prod_id:
            qs = qs.filter(pk=prod_id)

        total   = qs.count()
        updated = 0
        skipped = 0

        self.stdout.write(f"  تعداد محصولات: {total}\n")

        for product in qs.iterator():
            changes = generate_all_seo_fields(product, force=force)

            if not changes:
                skipped += 1
                continue

            self.stdout.write(f"\n  📦 {product.name} (id={product.pk})")
            for field, value in changes.items():
                display = value[:60] + '…' if len(str(value)) > 60 else value
                self.stdout.write(f"     {field}: {display}")

            if not dry_run:
                with transaction.atomic():
                    for field, value in changes.items():
                        setattr(product, field, value)
                    # save بدون trigger مجدد auto-SEO
                    Product.objects.filter(pk=product.pk).update(**changes)
                updated += 1
            else:
                updated += 1

        self.stdout.write("\n" + "─" * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] {updated} محصول تغییر می‌کرد | {skipped} بدون تغییر"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✓ {updated} محصول بروزرسانی شد | {skipped} بدون تغییر"
            ))
