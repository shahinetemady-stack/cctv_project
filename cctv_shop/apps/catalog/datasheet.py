"""
apps/catalog/datasheet.py

تبدیل دیتاشیت PDF محصول به تصاویر jpeg (یک تصویر به‌ازای هر صفحه) با poppler-utils.
هیچ استثنایی به بیرون پاس داده نمی‌شود — خرابی تبدیل نباید ذخیره محصول را بشکند.
"""
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.db import transaction

from .models import DatasheetPage

logger = logging.getLogger(__name__)

# حداکثر تعداد صفحاتی که به تصویر تبدیل می‌شود
MAX_PAGES = 20
DPI = 110

_PAGE_SUFFIX = re.compile(r"-(\d+)\.jpg$")


def clear_datasheet_pages(product):
    """حذف همه رکوردها و فایل‌های صفحات دیتاشیت یک محصول."""
    for p in product.datasheet_pages.all():
        p.image.delete(save=False)
        p.delete()


def convert_datasheet(product):
    """
    صفحات PDF دیتاشیت محصول را با pdftoppm به webp تبدیل و
    به‌صورت اتمیک جایگزین صفحات قبلی می‌کند.
    در صورت هر خطا فقط warning لاگ می‌شود.
    """
    try:
        if not product.datasheet_pdf:
            clear_datasheet_pages(product)
            return
        pdf_path = product.datasheet_pdf.path
        old_pages = list(product.datasheet_pages.all())

        with tempfile.TemporaryDirectory(prefix="datasheet_") as tmpdir:
            prefix = str(Path(tmpdir) / "page")
            subprocess.run(
                ["pdftoppm", "-jpeg", "-jpegopt", "quality=85", "-r", str(DPI),
                 "-f", "1", "-l", str(MAX_PAGES), pdf_path, prefix],
                check=True, capture_output=True, timeout=120,
            )
            files = sorted(Path(tmpdir).glob("page-*.jpg"))
            if not files:
                logger.warning("[datasheet] pdftoppm produced no pages for product %s", product.pk)
                return

            with transaction.atomic():
                product.datasheet_pages.all().delete()
                for f in files:
                    m = _PAGE_SUFFIX.search(f.name)
                    page_no = int(m.group(1)) if m else 0
                    with open(f, "rb") as fh:
                        DatasheetPage.objects.create(
                            product=product, page=page_no,
                            image=File(fh, name=f"page-{page_no}.jpg"),
                        )

        # فایل‌های قدیمی را بعد از کامیتی موفق تراکنش پاک کن
        for p in old_pages:
            if p.image:
                p.image.delete(save=False)
    except Exception as e:
        logger.warning("[datasheet] conversion failed for product %s: %s", product.pk, e)
