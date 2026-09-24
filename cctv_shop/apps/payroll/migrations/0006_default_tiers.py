# بذر پلکان‌های پیش‌فرض (پلکان پیش‌رونده با گام) برای سینگلتون تنظیمات
from django.db import migrations


def _seed_default_tiers(apps, schema_editor):
    # این ثابت‌ها بعداً از مدل حذف شدند؛ گارد تا اجرای مهاجرت روی دیتابیس تازه
    # (که جدول تنظیمات در آن خالی است و این تابع عملاً کاری نمی‌کند) نشکند.
    try:
        from apps.payroll.models import DEFAULT_GROWTH_TIERS, DEFAULT_TEAM_TIERS
    except ImportError:
        return

    PayrollSettings = apps.get_model("payroll", "PayrollSettings")
    for st in PayrollSettings.objects.all():
        def old_shape(tiers):
            return any(isinstance(t, dict) and "cap" not in t for t in (tiers or []))

        if not st.growth_bonus_tiers or old_shape(st.growth_bonus_tiers):
            st.growth_bonus_tiers = DEFAULT_GROWTH_TIERS
        if not st.team_bonus_tiers or old_shape(st.team_bonus_tiers):
            st.team_bonus_tiers = DEFAULT_TEAM_TIERS
        st.save(update_fields=["growth_bonus_tiers", "team_bonus_tiers"])


class Migration(migrations.Migration):

    dependencies = [
        ("payroll", "0005_remove_payrollprofile_growth_bonus_basis_and_more"),
    ]

    operations = [
        migrations.RunPython(_seed_default_tiers, migrations.RunPython.noop),
    ]
