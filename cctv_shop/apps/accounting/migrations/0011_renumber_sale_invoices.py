"""
شماره‌گذاری مجدد فاکتورهای فروش — تبدیل فرمت طولانی (INV-YYYYMMDD-XXXXXX)
به شماره‌های ساده و ترتیبی از ۱۰۰۰ (به ترتیب تاریخ ایجاد).
ارجاع‌های کاردکس (StockMovement.reference) و متن یادداشت‌هایشان هم اصلاح می‌شود.
"""
from django.db import migrations


def renumber_sale_invoices(apps, schema_editor):
    SaleInvoice = apps.get_model('accounting', 'SaleInvoice')
    StockMovement = apps.get_model('inventory', 'StockMovement')

    invoices = list(SaleInvoice.objects.order_by('created_at', 'id'))

    # فاکتورهایی که از قبل شماره عددی دارند دست نمی‌خورند؛ از ادامه آنها می‌رویم
    numeric = [int(inv.invoice_number) for inv in invoices if inv.invoice_number.isdigit()]
    next_num = max(numeric, default=999) + 1

    to_renumber = [inv for inv in invoices if not inv.invoice_number.isdigit()]
    old_numbers = {inv.id: inv.invoice_number for inv in to_renumber}

    # فاز ۱: شماره موقت برای جلوگیری از تداخل محدودیت unique
    for inv in to_renumber:
        SaleInvoice.objects.filter(id=inv.id).update(invoice_number=f'__tmp__{inv.id}')

    # فاز ۲: شماره نهایی + اصلاح ارجاع کاردکس
    for inv in to_renumber:
        old = old_numbers[inv.id]
        new = str(next_num)
        next_num += 1
        SaleInvoice.objects.filter(id=inv.id).update(invoice_number=new)
        for mv in StockMovement.objects.filter(reference=old):
            mv.reference = new
            if old in mv.note:
                mv.note = mv.note.replace(old, new)
            mv.save(update_fields=['reference', 'note'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0010_contact_opening_balance_cny_and_more'),
        ('inventory', '0004_alter_stockmovement_movement_type'),
    ]

    operations = [
        migrations.RunPython(renumber_sale_invoices, migrations.RunPython.noop),
    ]
