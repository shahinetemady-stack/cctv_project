# درصدها به تنظیمات منتقل شد + پلکان درصدی جداگانه (شخصی/مجموعه)
# ترتیب عملیات: ابتدا فیلدهای جدید، سپس تبدیل داده پلکان‌های قدیمی، و در انتها حذف فیلدهای قدیمی
from django.db import migrations, models

# کپی محلی (این مهاجرت تاریخی است و نباید به مدل وابسته بماند)
_DEFAULT_TIERS = [
    {"from": 0, "to": 60_000_000_000, "step": 10_000_000_000, "percent": 0.5},
    {"from": 60_000_000_000, "to": 100_000_000_000, "step": 10_000_000_000, "percent": 0.7},
    {"from": 100_000_000_000, "to": 150_000_000_000, "step": 10_000_000_000, "percent": 1.0},
]


def _to_percent_ranges(tiers):
    """{from,to,step,amount} یا {cap,step,amount} → بازه‌های درصدی
    (percent = amount/step*100)."""
    rows = [t for t in (tiers or []) if isinstance(t, dict)]
    if not rows:
        return None
    ranges = []
    prev = 0
    for t in sorted(rows, key=lambda x: float(x.get("from") if "from" in x else x.get("cap") or 0)):
        lo = float(t.get("from") if "from" in t else prev)
        hi = float(t["to"]) if "to" in t else float(t["cap"])
        step = float(t.get("step") or 0)
        amount = float(t.get("amount") or 0)
        if step > 0 and hi > lo:
            ranges.append({"from": int(lo), "to": int(hi),
                           "step": int(step),
                           "percent": round(amount / step * 100, 4)})
        prev = hi
    return ranges or None


def _convert_tiers(apps, schema_editor):
    PayrollSettings = apps.get_model("payroll", "PayrollSettings")
    for st in PayrollSettings.objects.all():
        converted = _to_percent_ranges(st.growth_bonus_tiers)  # فیلد هنوز حذف نشده
        for field in ("growth_personal_tiers", "growth_total_tiers"):
            if not getattr(st, field, None):
                setattr(st, field, converted or _DEFAULT_TIERS)
        st.save(update_fields=["growth_personal_tiers", "growth_total_tiers"])


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0008_tiers_cap_to_ranges'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollprofile',
            name='growth_bonus_basis',
            field=models.CharField(choices=[('personal', 'فروش شخصی'), ('total', 'فروش کل مجموعه')], default='personal', help_text='کدام جدول پلکان (شخصی یا مجموعه) برای این پرسنل اعمال شود', max_length=10, verbose_name='مبنای پلکان افزایش فروش'),
        ),
        migrations.AddField(
            model_name='payrollsettings',
            name='growth_personal_tiers',
            field=models.JSONField(blank=True, default=list, help_text='لیستی از {from, to, step, percent} — پلکان پیش‌رونده با بازه؛ درصدِ هر گام', verbose_name='پلکان پاداش افزایش فروش — فروش شخصی'),
        ),
        migrations.AddField(
            model_name='payrollsettings',
            name='growth_total_tiers',
            field=models.JSONField(blank=True, default=list, help_text='لیستی از {from, to, step, percent} — پلکان پیش‌رونده با بازه؛ درصدِ هر گام', verbose_name='پلکان پاداش افزایش فروش — فروش کل مجموعه'),
        ),
        migrations.AddField(
            model_name='payrollsettings',
            name='personal_commission_rate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='درصد پورسانت فروش شخصی'),
        ),
        migrations.AddField(
            model_name='payrollsettings',
            name='total_sales_share_rate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='درصد سهم فروش کل مجموعه'),
        ),
        migrations.RunPython(_convert_tiers, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='payrollprofile',
            name='personal_commission_rate',
        ),
        migrations.RemoveField(
            model_name='payrollprofile',
            name='total_sales_share_fixed',
        ),
        migrations.RemoveField(
            model_name='payrollprofile',
            name='total_sales_share_rate',
        ),
        migrations.RemoveField(
            model_name='payrollsettings',
            name='growth_bonus_basis',
        ),
        migrations.RemoveField(
            model_name='payrollsettings',
            name='growth_bonus_tiers',
        ),
    ]
