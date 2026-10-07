"""
سید اولیه امور تولید — یک‌بار اجرا روی سرور:
  manage.py seed_production
- دسته ریشه «دوربین و دستگاه ضبط» + زیردسته‌های «دوربین مداربسته مونتاژ» و «دستگاه ضبط (DVR/NVR)»
- ویژگی‌های پیش‌فرض دسته ریشه (CategorySpecField — به زیردسته‌ها هم می‌رسد)
- انبار مونتاژ اگر نبود ساخته می‌شود
ایده‌مپوتنت — تکرار اجرا چیزی را خراب نمی‌کند.
"""
from django.core.management.base import BaseCommand

from apps.catalog.models import Category, CategorySpecField
from apps.inventory.models import Warehouse

CAMERA_SPECS = [
    ("رزولوشن",       "select",   "2MP,4MP,5MP,8MP,12MP"),
    ("نوع لنز",       "select",   "فیکس,وریفکال,موتورایز"),
    ("فاصله کانونی",  "text",     ""),
    ("دید در شب",     "checkbox", ""),
]

RECORDER_SPECS = [
    ("نوع ضبط",       "select",   "DVR,NVR,XVR"),
    ("تعداد کانال",   "select",   "4,8,16,32"),
    ("ظرفیت هارد",    "text",     ""),
]


class Command(BaseCommand):
    help = "سید دسته «دوربین و دستگاه ضبط» + ویژگی‌ها + انبار مونتاژ"

    def handle(self, *args, **options):
        root, created = Category.objects.get_or_create(
            name="دوربین و دستگاه ضبط", parent=None,
            defaults={"category_type": "other", "sort_order": 0, "is_active": True},
        )
        self.stdout.write(("created" if created else "exists") + f": {root.name} (id={root.id})")

        subs = {}
        for sub in ("دوربین مداربسته", "دستگاه ضبط (DVR/NVR)"):
            c, created = Category.objects.get_or_create(
                name=sub, parent=root,
                defaults={"category_type": root.category_type, "is_active": True},
            )
            subs[sub] = c
            self.stdout.write(("  created" if created else "  exists") + f": {c.name} (id={c.id})")

        # ویژگی‌ها به تفکیک زیردسته — مشخصات دوربین و ضبط با هم فرق دارند
        for sub_name, specs in (("دوربین مداربسته", CAMERA_SPECS), ("دستگاه ضبط (DVR/NVR)", RECORDER_SPECS)):
            cat = subs[sub_name]
            for i, (label, ftype, choices) in enumerate(specs):
                f, created = CategorySpecField.objects.get_or_create(
                    category=cat, label=label,
                    defaults={"field_type": ftype, "choices": choices, "sort_order": i},
                )
                if created:
                    self.stdout.write(f"  spec [{sub_name}]: {label}")

        wh = Warehouse.objects.filter(warehouse_type=Warehouse.Type.ASSEMBLY).first()
        created = False
        if wh is None:
            wh = Warehouse.objects.create(
                code="ASM", name="انبار مونتاژ", warehouse_type=Warehouse.Type.ASSEMBLY,
            )
            created = True
        self.stdout.write(("created" if created else "exists") + f": warehouse {wh.name} (id={wh.id})")
        self.stdout.write(self.style.SUCCESS("seed_production done"))
