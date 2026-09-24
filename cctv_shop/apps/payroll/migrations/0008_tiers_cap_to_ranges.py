# تبدیل پلکان‌های ذخیره‌شده با فرمت قدیمی {cap, step, amount} به فرمت بازه‌ای {from, to, step, amount}
from django.db import migrations


def _cap_to_ranges(apps, schema_editor):
    PayrollSettings = apps.get_model("payroll", "PayrollSettings")
    for st in PayrollSettings.objects.all():
        tiers = st.growth_bonus_tiers or []
        if not tiers or all("cap" not in t for t in tiers if isinstance(t, dict)):
            continue
        converted = []
        prev = 0
        for t in sorted((x for x in tiers if isinstance(x, dict)),
                        key=lambda x: float(x.get("cap") or 0)):
            cap = float(t["cap"])
            converted.append({
                "from": prev,
                "to": int(cap),
                "step": t.get("step", 0),
                "amount": t.get("amount", 0),
            })
            prev = int(cap)
        st.growth_bonus_tiers = converted
        st.save(update_fields=["growth_bonus_tiers"])


class Migration(migrations.Migration):

    dependencies = [
        ("payroll", "0007_remove_payrollprofile_has_team_bonus_and_more"),
    ]

    operations = [
        migrations.RunPython(_cap_to_ranges, migrations.RunPython.noop),
    ]
