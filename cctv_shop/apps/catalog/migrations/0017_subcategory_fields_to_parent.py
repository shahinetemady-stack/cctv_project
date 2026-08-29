"""
قانون جدید: زیردسته‌ها ویژگی مستقل ندارند و همه‌چیز را از دسته اصلی می‌گیرند.
- ویژگی‌های سفارشیِ تعریف‌شده روی زیردسته‌ها (اگر باشند) به دسته والد منتقل می‌شوند
  (در صورت تکراری‌بودن key در والد، رکورد زیردسته حذف می‌شود)
- hidden_fields / field_overrides زیردسته‌ها پاک می‌شود (از والد به ارث می‌رسد)
"""
from django.db import migrations


def move_subcategory_fields_to_parent(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    CategorySpecField = apps.get_model('catalog', 'CategorySpecField')

    for field in CategorySpecField.objects.filter(category__parent__isnull=False).select_related('category__parent'):
        parent = field.category.parent
        dup = CategorySpecField.objects.filter(category=parent, key=field.key).exclude(pk=field.pk).exists()
        if dup:
            field.delete()
        else:
            field.category = parent
            field.save(update_fields=['category'])

    Category.objects.filter(parent__isnull=False).update(hidden_fields=[], field_overrides={})


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0016_exchange_rate_rial'),
    ]

    operations = [
        migrations.RunPython(move_subcategory_fields_to_parent, migrations.RunPython.noop),
    ]
