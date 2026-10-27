from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounting.models import (
    Account, Cheque, Contact, ExtraCost, Payment, PaymentReceipt, PurchaseInvoice,
    SaleInvoice, SaleItem, SalePayment, SettlementLine,
)
from apps.accounting.services import (
    available_customer_credit_irr, contact_operational_balance,
    consume_contact_credit, customer_balance_irr, delete_sale_payment,
    opening_remaining_irr, reallocate_sale_payment, recompute_invoice_status,
    settle_customer_fifo,
)
from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Order, OrderItem
from apps.payment.models import PaymentTransaction
from apps.payroll.models import Payslip
from apps.expenses.models import ExpenseCharge, Investor, InvestorMovement
from apps.users.models import User, UserProfile


class AccountingFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(phone="09120000000", password="test-pass")
        category = Category.objects.create(name="Test", slug="accounting-test")
        product = Product.objects.create(
            name="Accounting test product", slug="accounting-test-product", category=category,
        )
        cls.variant = ProductVariant.objects.create(
            product=product, sku="ACC-TEST-1", stock_quantity=1000,
            purchase_price_cny=0, shipping_cost_cny=0,
        )
        cls.bank = Account.objects.create(name="Bank", account_type="bank", currency="IRR")
        cls.petty = Account.objects.create(name="Petty", account_type="petty", currency="IRR")
        cls.foreign_account = Account.objects.create(
            name="CNY account", account_type="bank", currency="CNY",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self._user_seq = getattr(self, "_user_seq", 0)

    def make_user(self, *, opening=0, linked=True):
        self._user_seq += 1
        user = User.objects.create_user(
            phone=f"091210000{self._user_seq:02d}", password="test-pass",
            first_name="Test", last_name=f"Customer {self._user_seq}",
        )
        contact = None
        if linked:
            contact = Contact.objects.create(
                name=f"Contact {self._user_seq}", contact_type="customer",
                currency="IRR", opening_balance_irr=opening,
            )
        profile = UserProfile.objects.create(
            user=user, opening_balance_irr=0 if linked else opening,
            linked_contact=contact,
        )
        return user, profile, contact

    def make_invoice(self, user, amount, *, status="confirmed", order=None, number=None):
        invoice = SaleInvoice.objects.create(
            customer=user, customer_name=user.get_full_name(), status=status,
            currency="IRR", settlement="cash", issue_date=timezone.localdate(),
            order=order,
        )
        if number:
            invoice.invoice_number = number
            invoice.save(update_fields=["invoice_number"])
        SaleItem.objects.create(
            invoice=invoice, variant=self.variant, quantity=1, unit_price=amount,
        )
        SettlementLine.objects.create(
            invoice=invoice, settlement_type="cash", amount=amount,
            due_date=timezone.localdate(),
        )
        return invoice

    def make_order(self, user, amount):
        return Order.objects.create(
            user=user, status=Order.Status.AWAITING_PAYMENT,
            total_amount=amount, confirmed_amount=amount,
        )

    def payment_payload(self, contact, **overrides):
        payload = {
            "contact_id": contact.id,
            "direction": "in",
            "payment_type": "transfer",
            "currency": "IRR",
            "amount": 100,
            "rate_irr": 0,
            "date": str(timezone.localdate()),
            "to_account_id": self.bank.id,
            "confirm_duplicate": True,
        }
        payload.update(overrides)
        return payload

    def test_multi_invoice_delete_recomputes_every_invoice_and_order(self):
        user, _, _ = self.make_user()
        order1 = self.make_order(user, 100)
        order2 = self.make_order(user, 50)
        inv1 = self.make_invoice(user, 100, order=order1)
        inv2 = self.make_invoice(user, 50, order=order2)

        result = settle_customer_fifo(
            user, 150, date=timezone.localdate(), to_account_id=self.bank.id,
        )
        self.assertEqual(result["leftover"], 0)
        self.assertEqual(SalePayment.objects.count(), 1)
        inv1.refresh_from_db()
        inv2.refresh_from_db()
        self.assertEqual(inv1.status, SaleInvoice.Status.PAID)
        self.assertEqual(inv2.status, SaleInvoice.Status.PAID)
        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual((order1.paid_amount, order2.paid_amount), (100, 50))

        delete_sale_payment(SalePayment.objects.get())
        inv1.refresh_from_db()
        inv2.refresh_from_db()
        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual(inv1.status, SaleInvoice.Status.CONFIRMED)
        self.assertEqual(inv2.status, SaleInvoice.Status.CONFIRMED)
        self.assertEqual((inv1.remaining_amount, inv2.remaining_amount), (100, 50))
        self.assertEqual(order1.status, Order.Status.AWAITING_PAYMENT)
        self.assertEqual(order2.status, Order.Status.AWAITING_PAYMENT)
        self.assertEqual((order1.paid_amount, order2.paid_amount), (0, 0))
        self.assertEqual(self.bank.balance, 0)

    def test_invoice_void_rejects_allocation_from_shared_sale_payment(self):
        user, _, _ = self.make_user()
        inv1 = self.make_invoice(user, 100)
        inv2 = self.make_invoice(user, 50)
        settle_customer_fifo(user, 150, date=timezone.localdate())

        payment = SalePayment.objects.get()
        self.assertEqual(payment.invoice_id, inv1.id)
        self.assertFalse(inv2.sale_payments.exists())
        self.assertEqual(inv2.paid_amount, 50)

        response = self.client.post(f"/api/accounting/sale-invoices/{inv2.id}/void/")
        self.assertEqual(response.status_code, 400)
        inv2.refresh_from_db()
        self.assertEqual(inv2.status, SaleInvoice.Status.PAID)
        self.assertEqual(inv2.paid_amount, 50)
        self.assertTrue(inv2.settlement_lines.get().is_active)
        self.assertEqual(
            payment.allocations.filter(settlement_line__invoice=inv2).get().amount, 50,
        )

    def test_recompute_does_not_touch_closed_order_or_inventory(self):
        user, _, _ = self.make_user()
        order = self.make_order(user, 100)
        invoice = self.make_invoice(user, 100, order=order)
        settle_customer_fifo(user, 100, date=timezone.localdate())
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SaleInvoice.Status.PAID)

        order.status = Order.Status.REJECTED
        order.paid_amount = None
        order.payment_method = ""
        order.paid_at = None
        order.stock_deducted = False
        order.save(update_fields=[
            "status", "paid_amount", "payment_method", "paid_at", "stock_deducted", "updated_at",
        ])
        with patch("apps.orders.services.complete_order_inventory") as complete_inventory:
            recompute_invoice_status(invoice)
            complete_inventory.assert_not_called()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertIsNone(order.paid_amount)
        self.assertIsNone(order.paid_at)
        self.assertEqual(order.payment_method, "")
        self.assertFalse(order.stock_deducted)

    def test_reallocate_down_and_up_keeps_allocations_and_status_in_sync(self):
        user, _, _ = self.make_user()
        inv1 = self.make_invoice(user, 100)
        inv2 = self.make_invoice(user, 50)
        settle_customer_fifo(user, 150, date=timezone.localdate())
        payment = SalePayment.objects.get()

        payment.amount = 40
        payment.save(update_fields=["amount"])
        reallocate_sale_payment(payment)
        inv1.refresh_from_db()
        inv2.refresh_from_db()
        self.assertEqual((inv1.paid_amount, inv2.paid_amount), (40, 0))
        self.assertEqual(inv1.status, SaleInvoice.Status.CONFIRMED)
        self.assertEqual(inv2.status, SaleInvoice.Status.CONFIRMED)

        payment.refresh_from_db()
        payment.amount = 120
        payment.save(update_fields=["amount"])
        reallocate_sale_payment(payment)
        inv1.refresh_from_db()
        inv2.refresh_from_db()
        self.assertEqual((inv1.paid_amount, inv2.paid_amount), (100, 20))
        self.assertEqual(inv1.status, SaleInvoice.Status.PAID)
        self.assertEqual(inv2.status, SaleInvoice.Status.CONFIRMED)
        self.assertEqual(sum(a.amount for a in payment.allocations.all()), 120)

    def test_invoice_total_edit_with_allocations_is_rejected(self):
        user, _, _ = self.make_user()
        invoice = self.make_invoice(user, 100)
        settle_customer_fifo(user, 40, date=timezone.localdate())

        response = self.client.patch(
            f"/api/accounting/sale-invoices/{invoice.id}/",
            {"discount_amount": 10}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.discount_amount, 0)
        self.assertEqual(invoice.total_amount, 100)
        self.assertEqual(invoice.paid_amount, 40)

    def test_invalid_item_discount_does_not_create_invoice(self):
        user, _, _ = self.make_user()
        before = SaleInvoice.objects.count()
        response = self.client.post("/api/accounting/sale-invoices/", {
            "customer_id": user.id,
            "currency": "IRR",
            "settlement": "cash",
            "status": "draft",
            "items": [{
                "variant_id": self.variant.id, "quantity": 1,
                "unit_price": 100, "discount_percent": 200,
            }],
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SaleInvoice.objects.count(), before)

    def test_rejected_cheque_rolls_back_parent_payment(self):
        user, _, contact = self.make_user()
        other, _, _ = self.make_user()
        other_invoice = self.make_invoice(other, 100)
        before_payments = Payment.objects.count()
        before_cheques = Cheque.objects.count()
        payload = self.payment_payload(
            contact,
            payment_type="cheque",
            to_account_id=self.petty.id,
            cheques=[{
                "serial_number": "CH-ROLLBACK",
                "cheque_date": str(timezone.localdate()),
                "amount": 100,
                "sale_invoice_id": other_invoice.id,
            }],
        )
        response = self.client.post("/api/accounting/payments/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), before_payments)
        self.assertEqual(Cheque.objects.count(), before_cheques)

    def test_direction_currency_and_rate_validation_is_atomic(self):
        _, _, contact = self.make_user()
        before = Payment.objects.count()
        response = self.client.post(
            "/api/accounting/payments/",
            self.payment_payload(contact, direction="out", to_account_id=self.bank.id),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/accounting/payments/",
            self.payment_payload(contact, currency="CNY", rate_irr=0),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/accounting/payments/",
            self.payment_payload(contact, currency="IRR", to_account_id=self.foreign_account.id),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), before)

    def test_internal_transfer_is_paired_and_atomic(self):
        response = self.client.post("/api/accounting/payments/internal-transfer/", {
            "from_account_id": self.foreign_account.id,
            "to_account_id": self.bank.id,
            "amount": 2,
            "rate_irr": 1000,
            "date": str(timezone.localdate()),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        outgoing = Payment.objects.get(direction="out")
        incoming = Payment.objects.get(direction="in")
        self.assertEqual(outgoing.paired_with, incoming)
        self.assertEqual(incoming.paired_with, outgoing)
        self.assertEqual(incoming.amount, 2000)
        self.assertEqual(self.foreign_account.balance, -2)
        self.assertEqual(self.bank.balance, 2000)

        before = Payment.objects.count()
        rejected = self.client.post("/api/accounting/payments/internal-transfer/", {
            "from_account_id": self.foreign_account.id,
            "to_account_id": self.bank.id,
            "amount": 1,
            "rate_irr": 0,
            "date": str(timezone.localdate()),
        }, format="json")
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(Payment.objects.count(), before)

    def test_payment_clearing_prefers_unique_mellat_account(self):
        from apps.orders.services import _payment_clearing_account_id

        Account.objects.create(name="بانک دیگر", account_type="bank", currency="IRR")
        mellat = Account.objects.create(name="بانک ملت", account_type="bank", currency="IRR")
        self.assertEqual(_payment_clearing_account_id(), mellat.id)

    def test_opening_receipt_uses_linked_contact_and_dashboard_balance(self):
        user, profile, contact = self.make_user(opening=100)
        response = self.client.post(
            "/api/accounting/payments/",
            self.payment_payload(contact, amount=40, settle_target="opening"),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        payment = Payment.objects.get()
        self.assertEqual(payment.settlement_target, Payment.SettlementTarget.OPENING)
        self.assertEqual(opening_remaining_irr(user), 60)
        self.assertEqual(customer_balance_irr(user), 60)
        profile.refresh_from_db()
        self.assertEqual(profile.opening_balance_irr, 0)

        self.client.force_authenticate(user)
        dashboard = self.client.get("/api/accounting/my/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["debt_irr"], 60)
        kardex = self.client.get("/api/accounting/my/kardex/")
        self.assertEqual(kardex.status_code, 200)
        self.assertEqual(kardex.data["balance_irr"], 60)

    def test_contact_detail_total_includes_linked_documents_and_cash_credit(self):
        user, profile, contact = self.make_user(opening=100)
        self.make_invoice(user, 80)
        response = self.client.post(
            "/api/accounting/payments/",
            self.payment_payload(contact, amount=40, settle_target="opening"),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        payment = Payment.objects.get()
        profile.payment_credit_irr = 10
        profile.save(update_fields=["payment_credit_irr", "updated_at"])

        manual = self.client.get(f"/api/accounting/contacts/c_{contact.id}/")
        self.assertEqual(manual.status_code, 200, manual.data)
        self.assertIn(payment.id, [row["id"] for row in manual.data["payments"]])
        self.assertEqual(manual.data["balance_irr"], 60)
        self.assertEqual(manual.data["sale_debt"], 80)
        self.assertEqual(manual.data["total_balance_irr"], 130)

        registered_user, registered_profile, _ = self.make_user(opening=50, linked=False)
        self.make_invoice(registered_user, 20)
        registered_profile.payment_credit_irr = 5
        registered_profile.save(update_fields=["payment_credit_irr", "updated_at"])
        registered = self.client.get(f"/api/accounting/contacts/u_{registered_user.id}/")
        self.assertEqual(registered.status_code, 200, registered.data)
        self.assertEqual(registered.data["sale_debt"], 20)
        self.assertEqual(registered.data["total_balance_irr"], 65)

    def test_contact_detail_returns_complete_purchase_and_extra_cost_ledger(self):
        user, _, contact = self.make_user()
        invoices = [PurchaseInvoice.objects.create(
            supplier=contact,
            purchase_type=PurchaseInvoice.PurchaseType.DOMESTIC,
            rate_purchase_cny=1,
            date=timezone.localdate(),
        ) for _ in range(21)]
        ExtraCost.objects.create(
            invoice=invoices[0], contact=contact, cost_type="other", amount_irr=25,
        )
        cancelled = PurchaseInvoice.objects.create(
            supplier=contact,
            purchase_type=PurchaseInvoice.PurchaseType.DOMESTIC,
            rate_purchase_cny=1,
            date=timezone.localdate(),
            status=PurchaseInvoice.Status.CANCELLED,
        )

        response = self.client.get(f"/api/accounting/contacts/c_{contact.id}/")
        self.assertEqual(response.status_code, 200, response.data)
        supplier_rows = [row for row in response.data["invoices"] if row["role"] == "supplier"]
        extra_rows = [row for row in response.data["invoices"] if row["role"] == "extra"]
        self.assertEqual(len(supplier_rows), 21)
        self.assertEqual(len(extra_rows), 1)
        self.assertEqual(extra_rows[0]["amount_irr"], 25)
        self.assertNotIn(cancelled.id, [row["id"] for row in supplier_rows])
        self.assertEqual(response.data["total_balance_irr"], -25)

    def test_negative_opening_credit_consumption_and_reverse(self):
        user, _, contact = self.make_user(opening=-100)
        invoice = self.make_invoice(user, 100)
        self.assertEqual(available_customer_credit_irr(user), 100)

        result = consume_contact_credit(user, actor=self.admin)
        self.assertEqual(result["amount"], 100)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SaleInvoice.Status.PAID)
        source = Payment.objects.get(settlement_target=Payment.SettlementTarget.OPENING)
        self.assertEqual(source.derived_sale_payments.count(), 1)

        response = self.client.post(f"/api/accounting/payments/{source.id}/reverse/")
        self.assertEqual(response.status_code, 201, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SaleInvoice.Status.CONFIRMED)
        self.assertEqual(invoice.remaining_amount, 100)
        self.assertEqual(opening_remaining_irr(user), -100)
        self.assertEqual(available_customer_credit_irr(user), 100)
        self.assertFalse(SalePayment.objects.filter(source_payment=source).exists())
        self.assertEqual(contact.opening_balance_irr, -100)

    def test_voucher_reverse_restores_source_invoice(self):
        user, _, from_contact = self.make_user()
        invoice = self.make_invoice(user, 100)
        to_contact = Contact.objects.create(name="Destination", contact_type="other", currency="IRR")
        response = self.client.post("/api/accounting/payments/voucher/", {
            "from_contact_id": from_contact.id,
            "to_contact_id": to_contact.id,
            "currency": "IRR",
            "amount": 100,
            "date": str(timezone.localdate()),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SaleInvoice.Status.PAID)
        source = Payment.objects.get(contact=to_contact, direction="out")
        self.assertEqual(source.derived_sale_payments.count(), 1)

        response = self.client.post(f"/api/accounting/payments/{source.id}/reverse/")
        self.assertEqual(response.status_code, 201, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SaleInvoice.Status.CONFIRMED)
        self.assertEqual(invoice.remaining_amount, 100)
        self.assertFalse(SalePayment.objects.filter(source_payment=source).exists())

    def test_cheque_lifecycle_has_single_bank_and_contact_effect(self):
        user, _, contact = self.make_user()
        invoice = self.make_invoice(user, 100)
        original = Payment.objects.create(
            contact=contact, direction="in", payment_type="cheque", currency="IRR",
            amount=100, date=timezone.localdate(), to_account=self.petty,
        )
        cheque = Cheque.objects.create(
            payment=original, kind="received", status="in_hand",
            serial_number="CH-100", cheque_date=timezone.localdate(),
            amount=100, sale_invoice=invoice,
        )
        response = self.client.post(
            f"/api/accounting/cheques/{cheque.id}/action/",
            {"action": "deposit", "account_id": self.bank.id}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        invoice.refresh_from_db()
        cheque.refresh_from_db()
        self.assertEqual(cheque.status, "deposited")
        self.assertEqual(invoice.status, SaleInvoice.Status.PAID)
        self.assertEqual(self.bank.balance, 100)
        self.assertEqual(self.petty.balance, 0)
        self.assertEqual(contact_operational_balance(contact), 0)
        self.assertEqual(customer_balance_irr(user), 0)
        sale_payment = SalePayment.objects.get(cheque=cheque)
        self.assertIsNone(sale_payment.to_account)
        self.assertEqual(sale_payment.source_payment.settlement_target, Payment.SettlementTarget.CHEQUE)

        response = self.client.post(
            f"/api/accounting/cheques/{cheque.id}/action/",
            {"action": "bounce"}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SaleInvoice.Status.CONFIRMED)
        self.assertEqual(self.bank.balance, 0)
        self.assertEqual(self.petty.balance, 100)
        self.assertEqual(contact_operational_balance(contact), -100)
        self.assertEqual(customer_balance_irr(user), 0)

        response = self.client.post(
            f"/api/accounting/cheques/{cheque.id}/action/",
            {"action": "return"}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        invoice.refresh_from_db()
        self.assertEqual(self.petty.balance, 0)
        self.assertEqual(contact_operational_balance(contact), 0)
        self.assertEqual(customer_balance_irr(user), 100)
        self.assertEqual(invoice.remaining_amount, 100)

    def test_paid_invoice_cannot_accept_silent_new_receipt(self):
        user, _, _ = self.make_user()
        invoice = self.make_invoice(user, 100)
        settle_customer_fifo(user, 100, date=timezone.localdate(), to_account_id=self.bank.id)
        invoice.refresh_from_db()
        before = SalePayment.objects.count()
        response = self.client.post("/api/accounting/sale-payments/", {
            "invoice_id": invoice.id,
            "amount": 25,
            "method": "transfer",
            "to_account_id": self.bank.id,
            "date": str(timezone.localdate()),
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SalePayment.objects.count(), before)
        self.assertEqual(self.bank.balance, 100)

    def test_overpayment_and_contact_debt_are_not_double_counted_as_credit(self):
        user, _, contact = self.make_user()
        self.make_invoice(user, 100)
        settle_customer_fifo(user, 150, date=timezone.localdate())
        Payment.objects.create(
            contact=contact, direction="out", payment_type="other", currency="IRR",
            amount=50, date=timezone.localdate(),
        )
        self.assertEqual(customer_balance_irr(user), 0)
        self.assertEqual(available_customer_credit_irr(user), 50)

    def test_due_fifo_ignores_fully_paid_lines(self):
        user, _, _ = self.make_user()
        old = self.make_invoice(user, 100)
        old_line = old.settlement_lines.get()
        old_line.due_date = timezone.localdate() - timedelta(days=30)
        old_line.save(update_fields=["due_date"])
        newer = self.make_invoice(user, 50)
        newer_line = newer.settlement_lines.get()
        newer_line.due_date = timezone.localdate() - timedelta(days=20)
        newer_line.save(update_fields=["due_date"])
        newer_line.amount = 100
        newer_line.save(update_fields=["amount"])
        SaleItem.objects.create(invoice=newer, variant=self.variant, quantity=1, unit_price=50)

        settle_customer_fifo(user, 100, date=timezone.localdate())
        old.refresh_from_db()
        newer.refresh_from_db()
        self.assertEqual(old.status, SaleInvoice.Status.PAID)
        self.assertEqual(newer.status, SaleInvoice.Status.CONFIRMED)
        result = settle_customer_fifo(user, 50, date=timezone.localdate())
        self.assertEqual(result["allocated"][0]["invoice_id"], newer.id)

    def test_gateway_callback_completes_order_once(self):
        from apps.orders.services import process_payment_callback

        user, _, _ = self.make_user()
        order = self.make_order(user, 100)
        OrderItem.objects.create(
            order=order, variant=self.variant, quantity=1, unit_price=100,
            settlement_type="cash",
        )
        original_stock = self.variant.stock_quantity
        with patch("apps.notifications.services.notify_order_paid"), \
                patch("apps.notifications.services.notify_order_status_sms"), \
                patch("apps.users.services.maybe_notify_near_tier"):
            process_payment_callback(order, "REF-100", True)
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.paid_amount, 100)
        self.assertEqual(order.payment_method, "online")
        self.assertTrue(order.stock_deducted)
        self.assertEqual(self.variant.stock_quantity, original_stock - 1)
        self.assertEqual(SalePayment.objects.get().to_account_id, self.bank.id)
        self.assertEqual(self.bank.balance, 100)

        with self.assertRaises(ValueError):
            process_payment_callback(order, "REF-100", True)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, original_stock - 1)
        self.assertEqual(SalePayment.objects.count(), 1)

    def test_payment_initiation_reuses_active_transaction(self):
        from apps.payment.services import initiate_payment

        user, _, _ = self.make_user()
        order = self.make_order(user, 100)
        OrderItem.objects.create(
            order=order, variant=self.variant, quantity=1, unit_price=100,
            settlement_type="cash",
        )
        with patch("apps.payment.services.bp_pay_request", return_value={
                "success": True, "token": "TOKEN-REUSE"}):
            first = initiate_payment(order, None)
            second = initiate_payment(order, None)
        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertEqual(first["transaction_id"], second["transaction_id"])
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_second_successful_bank_transaction_is_reversed(self):
        from apps.payment.services import _finalize_success

        user, _, _ = self.make_user()
        order = self.make_order(user, 100)
        self.make_invoice(user, 100, order=order)
        PaymentTransaction.objects.create(
            order=order, user=user, amount=100, status="success", sale_order_id="1",
        )
        duplicate = PaymentTransaction.objects.create(
            order=order, user=user, amount=100, status="initiated", sale_order_id="2",
        )
        with patch("apps.payment.services.bp_verify_request", return_value={"success": True}), \
                patch("apps.payment.services.bp_settle_request") as settle_mock, \
                patch("apps.payment.services.bp_reverse_request") as reverse_mock:
            result = _finalize_success(duplicate, "2", "REF-DUP")
        self.assertFalse(result["success"])
        duplicate.refresh_from_db()
        self.assertEqual(duplicate.status, PaymentTransaction.Status.FAILED)
        reverse_mock.assert_called_once()
        settle_mock.assert_not_called()

    def test_receipt_approval_completes_inventory_and_order(self):
        user, _, _ = self.make_user()
        order = self.make_order(user, 100)
        OrderItem.objects.create(
            order=order, variant=self.variant, quantity=1, unit_price=100,
            settlement_type="cash",
        )
        receipt = PaymentReceipt.objects.create(
            order=order, customer=user, amount=100, paid_at=timezone.localdate(),
            image="receipts/test.jpg", status="pending",
        )
        original_stock = self.variant.stock_quantity
        with patch("apps.notifications.services.notify_receipt_approved"):
            response = self.client.post(f"/api/orders/admin/receipts/{receipt.id}/approve/")
        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        receipt.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(receipt.status, PaymentReceipt.Status.APPROVED)
        self.assertIsNotNone(receipt.sale_payment)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.paid_amount, 100)
        self.assertTrue(order.stock_deducted)
        self.assertEqual(self.variant.stock_quantity, original_stock - 1)

    def test_inquiry_confirmation_propagates_settlement_override(self):
        from apps.orders.services import confirm_inquiry_order

        user, _, _ = self.make_user()
        order = Order.objects.create(
            user=user, order_type="inquiry", status="pending", total_amount=200,
        )
        OrderItem.objects.create(
            order=order, variant=self.variant, quantity=1, unit_price=100,
            settlement_type="cash",
        )
        OrderItem.objects.create(
            order=order, variant=self.variant, quantity=1, unit_price=100,
            settlement_type="credit",
        )
        due = timezone.localdate() + timedelta(days=45)
        with patch("apps.notifications.services.notify_inquiry_confirmed"), \
                patch("apps.notifications.services.notify_order_status_sms"), \
                patch("apps.notifications.services.notify_account_info_sms"):
            confirm_inquiry_order(
                order, self.admin, 200, settlement_type="month1",
                settlement_due_date=due, sarraf_account_number="123",
                sarraf_account_holder="Sarraf", staff=self.admin,
            )
        invoice = order.sale_invoice
        self.assertEqual(invoice.total_amount, 200)
        self.assertEqual(invoice.settlement, "month1")
        self.assertEqual(invoice.due_date, due)
        self.assertEqual(sum(line.amount for line in invoice.settlement_lines.all()), 200)
        self.assertTrue(all(line.due_date == due for line in invoice.settlement_lines.all()))
        self.assertTrue(all(line.settlement_type == "month1" for line in invoice.settlement_lines.all()))

    def test_cancel_order_requires_receipt_reversal(self):
        from apps.orders.services import cancel_order

        user, _, _ = self.make_user()
        order = self.make_order(user, 100)
        invoice = self.make_invoice(user, 100, order=order)
        cancel_order(order, reason="test")
        order.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(invoice.status, SaleInvoice.Status.CANCELLED)

        order2 = self.make_order(user, 100)
        invoice2 = self.make_invoice(user, 100, order=order2)
        settle_customer_fifo(user, 40, date=timezone.localdate())
        with self.assertRaises(ValueError):
            cancel_order(order2, reason="test")
        order2.refresh_from_db()
        invoice2.refresh_from_db()
        self.assertEqual(order2.status, Order.Status.AWAITING_PAYMENT)
        self.assertEqual(invoice2.status, SaleInvoice.Status.CONFIRMED)

    def test_payslip_confirm_pay_zero_and_reverse(self):
        user, _, contact = self.make_user()
        slip = Payslip.objects.create(
            staff=user, year=2026, month=8, status="draft",
            gross_amount=100, net_amount=100,
        )
        response = self.client.post(f"/api/payroll/payslips/{slip.id}/confirm/")
        self.assertEqual(response.status_code, 200, response.data)
        slip.refresh_from_db()
        self.assertIsNotNone(slip.accrual_payment)
        self.assertEqual(slip.accrual_payment.contact_id, contact.id)

        before = Payment.objects.count()
        response = self.client.post(f"/api/payroll/payslips/{slip.id}/pay/", {
            "account_id": self.bank.id, "date": str(timezone.localdate()), "amount": 0,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), before)

        response = self.client.post(f"/api/payroll/payslips/{slip.id}/pay/", {
            "account_id": self.bank.id, "date": str(timezone.localdate()), "amount": 40,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        slip.refresh_from_db()
        self.assertEqual(slip.paid_amount, 40)
        payment_id = response.data["payment_id"]
        self.assertEqual(self.bank.balance, -40)

        response = self.client.post(f"/api/accounting/payments/{payment_id}/reverse/")
        self.assertEqual(response.status_code, 201, response.data)
        slip.refresh_from_db()
        self.assertEqual(slip.paid_amount, 0)
        self.assertEqual(slip.status, Payslip.Status.CONFIRMED)
        self.assertEqual(self.bank.balance, 0)

    def test_expense_allocation_ownership_and_reverse(self):
        from apps.expenses.services import book_charge_accrual, pay_charge

        user, _, contact = self.make_user()
        _, _, other_contact = self.make_user()
        charge = ExpenseCharge.objects.create(
            source="general", title="Test expense", contact=contact,
            year=2026, month=8, date=timezone.localdate(), amount=100,
            status="confirmed",
        )
        book_charge_accrual(charge)
        before = Payment.objects.count()
        response = self.client.post(
            "/api/accounting/payments/",
            self.payment_payload(
                other_contact, direction="out", from_account_id=self.bank.id,
                expense_charge_id=charge.id,
            ), format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), before)
        charge.refresh_from_db()
        self.assertEqual(charge.paid_amount, 0)

        payment = pay_charge(charge, self.bank, timezone.localdate(), amount=60)
        charge.refresh_from_db()
        self.assertEqual(charge.paid_amount, 60)
        response = self.client.post(f"/api/accounting/payments/{payment.id}/reverse/")
        self.assertEqual(response.status_code, 201, response.data)
        charge.refresh_from_db()
        self.assertEqual(charge.paid_amount, 0)
        self.assertEqual(charge.status, ExpenseCharge.Status.CONFIRMED)
        self.assertEqual(self.bank.balance, 0)

    def test_investor_movement_validation_and_reverse(self):
        _, _, contact = self.make_user()
        investor = Investor.objects.create(contact=contact, annual_rate=10)
        response = self.client.post("/api/expenses/investor-movements/", {
            "investor": investor.id, "movement_type": "withdraw",
            "amount": 40, "date": str(timezone.localdate()),
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvestorMovement.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

        response = self.client.post("/api/expenses/investor-movements/", {
            "investor": investor.id, "movement_type": "deposit", "account": self.bank.id,
            "amount": 100, "date": str(timezone.localdate()),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post("/api/expenses/investor-movements/", {
            "investor": investor.id, "movement_type": "withdraw", "account": self.bank.id,
            "amount": 40, "date": str(timezone.localdate()),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        investor.refresh_from_db()
        self.assertEqual(investor.principal, 60)
        self.assertEqual(self.bank.balance, 60)
        withdrawal = InvestorMovement.objects.get(movement_type="withdraw")

        response = self.client.post(f"/api/accounting/payments/{withdrawal.payment_id}/reverse/")
        self.assertEqual(response.status_code, 201, response.data)
        investor.refresh_from_db()
        self.assertEqual(investor.principal, 100)
        self.assertEqual(self.bank.balance, 100)
        self.assertTrue(InvestorMovement.objects.filter(payment__reversal_of=withdrawal.payment).exists())
