"""
python manage.py import_doorbinkar [--file scripts/output/doorbinkar_products.json] [--dry-run]

ایمپورت محصولات استخراج‌شده از سایت قدیمی doorbinkar.com
(خروجی scripts/scrape_doorbinkar.py).

نکته‌ها:
- نگاشت دسته از روی legacy_id دسته (مایگریشن catalog/0019).
- slug محصول همان slug لاتین سایت قدیمی است تا URL پایدار بماند.
- قیمت تومانی قدیم ÷ نرخ روز یوان → purchase_price_cny با سود ۰٪
  تا قیمت نمایشی برابر سایت قدیمی بماند؛ حاشیه سود بعداً اصلاح شود.
- موجودی: اگر در سایت قدیمی «افزودن به سبد» فعال بود ۱۰۰، وگرنه ۰
  (عدد نمادین — انبار واقعی باید بعداً به‌روزرسانی شود).
"""

import json
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import (
    Category,
    ExchangeRateSetting,
    Product,
    ProductImage,
    ProductVariant,
)


class Command(BaseCommand):
    help = "ایمپورت محصولات doorbinkar.com از JSON اسکریپر"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="scripts/output/doorbinkar_products.json",
            help="مسیر فایل JSON خروجی اسکریپر",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        path = options["file"]
        if not os.path.exists(path):
            self.stderr.write(f"فایل یافت نشد: {path}")
            return

        products_data = json.load(open(path, encoding="utf-8"))
        cats = {c.legacy_id: c for c in Category.objects.filter(legacy_id__isnull=False)}
        rate_toman = Decimal(ExchangeRateSetting.get_instance().rate_cny_to_irt) / 10

        created = updated = skipped = 0
        errors = []

        for row in products_data:
            legacy_id = row.get("legacy_id")
            name = (row.get("name") or "").strip()
            cat = cats.get(row.get("category_legacy_id"))
            if not name or not cat:
                skipped += 1
                errors.append(f"{legacy_id}: نام یا دسته نامعتبر (cat={row.get('category_legacy_id')})")
                continue

            price_toman = row.get("price_toman") or 0
            purchase_cny = round(Decimal(price_toman) / rate_toman, 2) if price_toman else Decimal(0)

            if options["dry_run"]:
                created += 1
                continue

            try:
                with transaction.atomic():
                    defaults = {
                        "name": name,
                        "category": cat,
                        "description": row.get("description") or "",
                        "short_description": (row.get("meta_description") or "")[:500],
                        "meta_title": (row.get("meta_title") or "")[:60],
                        "meta_description": (row.get("meta_description") or "")[:160],
                        "keywords": (row.get("keywords") or "")[:500],
                        "is_active": True,
                    }
                    product = Product.objects.filter(legacy_id=legacy_id).first()
                    if product:
                        for k, v in defaults.items():
                            setattr(product, k, v)
                        # اسلاگ دست‌نخورده می‌ماند تا URL ثابت بماند
                        product.save()
                        updated += 1
                    else:
                        slug = (row.get("legacy_slug") or "").strip()
                        if slug and Product.objects.filter(slug=slug).exists():
                            slug = f"{slug}-{legacy_id}"
                        product = Product.objects.create(
                            legacy_id=legacy_id, slug=slug or None, **defaults
                        )
                        created += 1

                    ProductVariant.objects.update_or_create(
                        sku=f"DK-{legacy_id}",
                        defaults={
                            "product": product,
                            "purchase_price_cny": purchase_cny,
                            "shipping_cost_cny": 0,
                            "profit_percent": 0,
                            "stock_quantity": 100 if row.get("in_stock") else 0,
                            "is_active": True,
                        },
                    )

                    # تصاویر — فقط اگر محصول تصویر ندارد
                    if not product.images.exists():
                        for i, rel_path in enumerate(row.get("images") or []):
                            ProductImage.objects.create(
                                product=product,
                                image=rel_path,
                                alt_text=name,
                                is_primary=(i == 0),
                                sort_order=i,
                            )
            except Exception as e:
                errors.append(f"{legacy_id} ({name[:30]}): {e}")

        self.stdout.write(f"✓ ساخته شد: {created}")
        self.stdout.write(f"✓ به‌روزرسانی: {updated}")
        if skipped:
            self.stdout.write(f"✗ رد شده: {skipped}")
        if errors:
            self.stdout.write(f"✗ خطاها ({len(errors)}):")
            for e in errors[:10]:
                self.stdout.write(f"  - {e}")
