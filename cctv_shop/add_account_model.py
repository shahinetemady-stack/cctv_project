"""
python add_account_model.py
اضافه کردن مدل Account (صندوق/بانک) و اصلاح Payment
اجرا در پوشه cctv_shop
"""
import os, sys, subprocess

# ─── 1. آپدیت models.py ──────────────────────────────────────
models_path = os.path.join("apps", "accounting", "models.py")
with open(models_path, encoding="utf-8") as f:
    content = f.read()

# اضافه کردن مدل Account بعد از Contact
account_model = '''

class Account(models.Model):
    """حساب بانکی / صندوق / تنخواه"""

    class AccountType(models.TextChoices):
        CASH      = "cash",      "صندوق نقد"
        BANK      = "bank",      "حساب بانکی"
        PETTY     = "petty",     "تنخواه"
        VIRTUAL   = "virtual",   "کیف پول / ارزی"

    class Currency(models.TextChoices):
        IRR = "IRR", "ریال"
        CNY = "CNY", "یوان"
        USD = "USD", "دلار"

    name         = models.CharField(max_length=100, verbose_name="نام حساب")
    account_type = models.CharField(max_length=20, choices=AccountType.choices, verbose_name="نوع")
    currency     = models.CharField(max_length=5, choices=Currency.choices, default=Currency.IRR, verbose_name="ارز")
    bank_name    = models.CharField(max_length=100, blank=True, verbose_name="نام بانک")
    account_number = models.CharField(max_length=50, blank=True, verbose_name="شماره حساب / کارت")
    initial_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="موجودی اولیه")
    is_active    = models.BooleanField(default=True, verbose_name="فعال")
    note         = models.TextField(blank=True, verbose_name="توضیحات")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounting_account"
        verbose_name = "حساب بانکی / صندوق"
        verbose_name_plural = "حساب‌های بانکی / صندوق"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()}) — {self.currency}"

    @property
    def balance(self):
        """موجودی فعلی = موجودی اولیه + دریافتی‌ها - پرداختی‌ها"""
        from django.db.models import Sum
        paid_out = self.payments_out.aggregate(s=Sum('amount'))['s'] or 0
        paid_in  = self.payments_in.aggregate(s=Sum('amount'))['s'] or 0
        return float(self.initial_balance) + float(paid_in) - float(paid_out)

'''

# اضافه کردن account_model قبل از Payment
if 'class Account' not in content:
    content = content.replace('class Payment(models.Model):', account_model + 'class Payment(models.Model):')

# آپدیت Payment — اضافه کردن from_account و to_account
old_payment_fields = '''    contact      = models.ForeignKey(Contact, on_delete=models.PROTECT,
                      related_name="payments", verbose_name="طرف حساب")
    invoice      = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments", verbose_name="فاکتور مرتبط")
    direction    = models.CharField(max_length=5, choices=Direction.choices, verbose_name="جهت")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, verbose_name="نوع")'''

new_payment_fields = '''    contact      = models.ForeignKey(Contact, on_delete=models.PROTECT,
                      null=True, blank=True,
                      related_name="payments", verbose_name="طرف حساب")
    invoice      = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments", verbose_name="فاکتور مرتبط")
    from_account = models.ForeignKey('Account', on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments_out",
                      verbose_name="از حساب (پرداختی)")
    to_account   = models.ForeignKey('Account', on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments_in",
                      verbose_name="به حساب (دریافتی)")
    direction    = models.CharField(max_length=5, choices=Direction.choices, verbose_name="جهت")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, verbose_name="نوع")'''

if 'from_account' not in content:
    content = content.replace(old_payment_fields, new_payment_fields)

with open(models_path, "w", encoding="utf-8") as f:
    f.write(content)
print("✓ models.py آپدیت شد")

# ─── 2. آپدیت admin.py ───────────────────────────────────────
admin_path = os.path.join("apps", "accounting", "admin.py")
with open(admin_path, encoding="utf-8") as f:
    admin = f.read()

# اضافه کردن Account به import و admin
if 'Account' not in admin:
    admin = admin.replace(
        'from .models import Contact, PurchaseInvoice, PurchaseItem, ExtraCost, Payment',
        'from .models import Contact, Account, PurchaseInvoice, PurchaseItem, ExtraCost, Payment'
    )
    # اصلاح PaymentInline
    admin = admin.replace(
        "    fields = [\"direction\", \"payment_type\", \"currency\", \"amount\", \"rate_irr\", \"date\", \"reference\"]",
        "    fields = [\"contact\", \"from_account\", \"to_account\", \"direction\", \"payment_type\", \"currency\", \"amount\", \"rate_irr\", \"date\", \"reference\"]\n    autocomplete_fields = []"
    )
    # اضافه کردن AccountAdmin
    admin += '''

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display  = ["name", "account_type", "currency", "bank_name", "account_number", "balance", "is_active"]
    list_filter   = ["account_type", "currency", "is_active"]
    search_fields = ["name", "bank_name", "account_number"]
    readonly_fields = ["balance"]
'''
    with open(admin_path, "w", encoding="utf-8") as f:
        f.write(admin)
    print("✓ admin.py آپدیت شد")
else:
    print("✓ admin.py قبلاً آپدیت شده بود")

# ─── 3. آپدیت views.py — اضافه کردن AccountListView و اصلاح PaymentCreateView ─
views_path = os.path.join("apps", "accounting", "views.py")
with open(views_path, encoding="utf-8") as f:
    views = f.read()

if 'AccountListView' not in views:
    account_view = '''

# ─── Accounts ────────────────────────────────────────────────

class AccountListView(APIView):
    """GET /api/accounting/accounts/ — لیست صندوق‌ها و حساب‌های بانکی"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import Account
        accounts = Account.objects.filter(is_active=True)
        return Response([{
            "id": a.id,
            "name": a.name,
            "account_type": a.account_type,
            "account_type_display": a.get_account_type_display(),
            "currency": a.currency,
            "bank_name": a.bank_name,
            "account_number": a.account_number,
            "balance": a.balance,
        } for a in accounts])

    def post(self, request):
        from .models import Account
        d = request.data
        a = Account.objects.create(
            name=d["name"],
            account_type=d.get("account_type", "cash"),
            currency=d.get("currency", "IRR"),
            bank_name=d.get("bank_name", ""),
            account_number=d.get("account_number", ""),
            initial_balance=d.get("initial_balance", 0),
            note=d.get("note", ""),
        )
        return Response({"id": a.id, "name": a.name}, status=201)
'''
    views = views.replace('# ─── Contacts', account_view + '\n# ─── Contacts')

# اصلاح PaymentCreateView — اضافه کردن from_account و to_account
old_pay = "                invoice_id=d.get(\"invoice_id\") or None,\n                direction=d[\"direction\"],"
new_pay = "                invoice_id=d.get(\"invoice_id\") or None,\n                from_account_id=d.get(\"from_account_id\") or None,\n                to_account_id=d.get(\"to_account_id\") or None,\n                direction=d[\"direction\"],"
views = views.replace(old_pay, new_pay)

with open(views_path, "w", encoding="utf-8") as f:
    f.write(views)
print("✓ views.py آپدیت شد")

# ─── 4. آپدیت urls.py ────────────────────────────────────────
urls_path = os.path.join("apps", "accounting", "urls.py")
with open(urls_path, encoding="utf-8") as f:
    urls = f.read()

if 'accounts/' not in urls:
    urls = urls.replace(
        'path("contacts/", views.ContactListView.as_view()),',
        'path("accounts/", views.AccountListView.as_view()),\n    path("contacts/", views.ContactListView.as_view()),'
    )
    with open(urls_path, "w", encoding="utf-8") as f:
        f.write(urls)
    print("✓ urls.py آپدیت شد")

# ─── 5. Migration ─────────────────────────────────────────────
r = subprocess.run([sys.executable, "manage.py", "makemigrations", "accounting"],
                   capture_output=True, text=True)
print(r.stdout[-400:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:"); print(r.stderr[-500:])
else:
    r2 = subprocess.run([sys.executable, "manage.py", "migrate"],
                        capture_output=True, text=True)
    print(r2.stdout[-300:] if r2.stdout else "")
    if r2.returncode != 0:
        print("خطای migrate:"); print(r2.stderr[-500:])

r3 = subprocess.run([sys.executable, "manage.py", "check", "--verbosity=0"],
                    capture_output=True, text=True)
if r3.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print((r3.stdout + r3.stderr)[-500:])
