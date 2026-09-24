"""
اصلاح یک‌بارهٔ دریافت‌های قدیمی که روی کارتابل طرف حساب نشسته‌اند در حالی که
مشتری فاکتور فروش باز داشته (مثل پرداخت کاووسی).

حالت پیش‌فرض — دریافت‌های نقدی/واریزی:
کاندید: Payment با direction=in، ارز IRR، نوع cash/transfer، بدون سند برگشت،
بدون جفت انتقالی، متعلق به طرف حسابِ لینک‌شده به کاربر سایت که فاکتور باز دارد.
--apply: سند برگشت می‌سازد (مانده کارتابل خنثی، موجودی بانک برمی‌گردد) و بعد
همان مبلغ با settle_customer_fifo روی فاکتورها تخصیص می‌یابد (موجودی بانک از
مسیر SalePayment دوباره درست می‌شود — خالص صفر).

حالت --transfer-legs — پاهای بستانکاریِ اسناد انتقال قدیمی:
سند انتقال «از X به Y» قبل از اصلاح PaymentVoucherView، بدهی فاکتورهای X را
تسویه نمی‌کرد — فقط یک بستانکاری روی کارتابل X می‌گذاشت و فاکتورها باز
می‌ماندند (مثل سند کاووسی → آرکا). این حالت برای هر پایهٔ in جفت‌شده که طرف
حسابش کاربر سایه با فاکتور باز دارد:
  ۱. به اندازهٔ بدهی فاکتورها (حداکثر مبلغ سند) FIFO تسویه می‌کند؛
  ۲. سند برگشتِ همان پایه را فقط به همان اندازه می‌سازد تا بستانکاریِ مصرف‌شده
     در کارتابل دوبار حساب نشود.
پایهٔ مقصد (بدهی طرف مقابل، مثل آرکا) دست نمی‌خورد — آن بدهی واقعی است.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "تخصیص مجدد دریافت‌های قدیمیِ کارتابل به فاکتورهای باز (FIFO)"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="بدون این فلگ فقط گزارش می‌دهد (dry-run)")
        parser.add_argument("--transfer-legs", action="store_true",
                            help="پردازش پاهای بستانکاریِ اسناد انتقال جفت‌شده (به‌جای دریافت‌های نقدی/واریزی)")

    def handle(self, *args, **opts):
        from apps.accounting.models import Payment, SaleInvoice
        from apps.accounting.services import settle_customer_fifo
        from apps.users.models import User, UserProfile

        apply = opts["apply"]
        transfer_legs = opts["transfer_legs"]
        today = timezone.localdate()

        linked = {p.linked_contact_id: p.user_id
                  for p in UserProfile.objects.filter(linked_contact__isnull=False)
                  .select_related("user") if p.user.is_active}

        if transfer_legs:
            candidates = (
                Payment.objects
                .filter(direction="in", currency="IRR",
                        reversal_of__isnull=True, paired_with__isnull=False,
                        reversals__isnull=True,
                        contact_id__in=linked.keys())
                .select_related("contact", "to_account", "paired_with")
                .order_by("date", "id")
            )
        else:
            candidates = (
                Payment.objects
                .filter(direction="in", currency="IRR",
                        payment_type__in=["cash", "transfer"],
                        reversal_of__isnull=True, paired_with__isnull=True,
                        reversals__isnull=True,
                        contact_id__in=linked.keys())
                .select_related("contact", "to_account")
                .order_by("date", "id")
            )

        total_done = 0
        for p in candidates:
            user_id = linked.get(p.contact_id)
            open_invs = [
                i for i in SaleInvoice.objects.filter(
                    customer_id=user_id, status="confirmed", currency="IRR")
                .prefetch_related("items", "sale_payments")
                if i.remaining_amount > 0
            ]
            if not open_invs:
                continue

            if transfer_legs:
                # فقط به اندازهٔ بدهی فاکتورها — مازاد سند انتقال بستانکاری
                # واقعی است و در کارتابل می‌ماند.
                budget = min(int(p.amount),
                             sum(i.remaining_amount for i in open_invs))
                if budget <= 0:
                    continue
                pair = p.paired_with
                self.stdout.write(
                    f"سند انتقال #{p.id} (جفت #{pair.id if pair else '-'}) | {p.contact.name} | "
                    f"{int(p.amount):,} ریال | {p.date} | تخصیص: {budget:,} | "
                    f"فاکتورهای باز: {', '.join(f'{i.invoice_number} (مانده {i.remaining_amount:,})' for i in open_invs)}"
                )
                if not apply:
                    continue
                with transaction.atomic():
                    r = settle_customer_fifo(
                        User.objects.get(id=user_id),
                        budget,
                        date=p.date,
                        method="transfer",
                        note=f"سند انتقال به {pair.contact.name if pair and pair.contact else '?'} — تخصیص سند #{p.id}",
                    )
                    allocated_total = sum(a["amount"] for a in r["allocated"])
                    if allocated_total > 0:
                        # برگشت جزئی پایهٔ بستانکاری به اندازهٔ مصرف‌شده — تا
                        # در خالص کارتابل دوبار حساب نشود. سابقه حفظ می‌شود.
                        Payment.objects.create(
                            contact_id=p.contact_id,
                            direction="out",
                            from_account_id=p.to_account_id,
                            to_account_id=p.from_account_id,
                            payment_type=p.payment_type,
                            currency=p.currency,
                            amount=allocated_total,
                            rate_irr=p.rate_irr,
                            date=today,
                            reference=p.reference,
                            note=f"برگشت سند #{p.id} مورخ {p.date} — تخصیص بستانکاری انتقالی به فاکتور" +
                                 (f" — {p.note}" if p.note else ""),
                            reversal_of=p,
                        )
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ تخصیص یافت: "
                        + ", ".join(f"{a['invoice_number']}←{a['amount']:,}" for a in r["allocated"])
                    ))
                    total_done += 1
                continue

            self.stdout.write(
                f"سند #{p.id} | {p.contact.name} | {int(p.amount):,} ریال | {p.date} | "
                f"فاکتورهای باز: {', '.join(f'{i.invoice_number} (مانده {i.remaining_amount:,})' for i in open_invs)}"
            )
            if not apply:
                continue

            with transaction.atomic():
                # سند برگشت — دقیقاً مثل PaymentReverseView
                Payment.objects.create(
                    contact_id=p.contact_id,
                    direction="out",
                    from_account_id=p.to_account_id,
                    to_account_id=p.from_account_id,
                    payment_type=p.payment_type,
                    currency=p.currency,
                    amount=p.amount,
                    rate_irr=p.rate_irr,
                    date=today,
                    reference=p.reference,
                    note=f"برگشت سند #{p.id} مورخ {p.date} — تخصیص مجدد به فاکتور" +
                         (f" — {p.note}" if p.note else ""),
                    reversal_of=p,
                )
                r = settle_customer_fifo(
                    User.objects.get(id=user_id),
                    int(p.amount),
                    date=p.date,
                    method="transfer" if p.payment_type == "transfer" else "cash",
                    to_account_id=p.to_account_id,
                    reference=p.reference or "",
                    note=f"تخصیص مجدد سند #{p.id}" + (f" — {p.note}" if p.note else ""),
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ برگشت خورد و تخصیص یافت: "
                    + ", ".join(f"{a['invoice_number']}←{a['amount']:,}" for a in r["allocated"])
                    + (f" | مازاد به بستانکاری: {r['leftover']:,}" if r["leftover"] else "")
                ))
                total_done += 1

        if not apply:
            self.stdout.write("\nحالت dry-run — برای اعمال: --apply")
        else:
            self.stdout.write(self.style.SUCCESS(f"\n{total_done} سند اصلاح شد"))
