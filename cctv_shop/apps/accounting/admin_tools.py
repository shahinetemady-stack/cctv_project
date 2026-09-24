"""
apps/accounting/admin_tools.py — v3
ابزارهای ادمین (ریست + بک‌اپ + بازیابی)
"""
import logging
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.views import View
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from django.db import transaction

logger = logging.getLogger(__name__)

# لینک‌های بالای Django admin
admin.site.site_header = mark_safe(
    'DOORBINKAR ─ '
    '<a href="/api/accounting/backup-page/" '
    'style="color:#28a745;text-decoration:none;font-weight:bold;margin-left:8px;">'
    '📦 بک‌اپ</a> '
    '<a href="/api/accounting/backup-restore-page/" '
    'style="color:#0066cc;text-decoration:none;font-weight:bold;margin-left:8px;">'
    '🔄 بازیابی</a> '
    '<a href="/api/accounting/system-reset-page/" '
    'style="color:#ffc107;text-decoration:none;font-weight:bold;">'
    '🗑 ریست سیستم</a>'
)
admin.site.site_title = 'DOORBINKAR Admin'
admin.site.index_title = 'مدیریت سیستم DOORBINKAR'


# ═══════════════════════════════════════════════════════════════
# منطق ریست
# ═══════════════════════════════════════════════════════════════

@transaction.atomic
def _soft_reset():
    from apps.accounting.models import (
        PurchaseInvoice, PurchaseItem, ExtraCost,
        SaleInvoice, SaleItem, SalePayment, Payment,
        PaymentReceipt,
    )
    from apps.orders.models import (
        Order, OrderItem, StockReservation, PaymentLog,
        Cart, CartItem, InquiryCart, InquiryCartItem,
    )
    from apps.payment.models import PaymentTransaction
    from apps.catalog.models import ProductVariant
    from apps.inventory.models import StockMovement, WarehouseStock, StockTransfer

    report = {
        "فاکتورهای خرید": PurchaseInvoice.objects.count(),
        "فاکتورهای فروش": SaleInvoice.objects.count(),
        "پرداخت‌ها": Payment.objects.count(),
        "سفارش‌های سایت": Order.objects.count(),
        "فیش‌های واریزی": PaymentReceipt.objects.count(),
        "تراکنش‌های درگاه": PaymentTransaction.objects.count(),
        "سبدهای خرید": Cart.objects.count() + InquiryCart.objects.count(),
        "حرکات کاردکس": StockMovement.objects.count(),
    }
    # فیش‌های واریزی و تراکنش‌های درگاه FK محافظت‌شده (PROTECT) به سفارش
    # و کاربر دارند — باید قبل از حذف سفارش‌ها/کاربران پاک شوند.
    PaymentReceipt.objects.all().delete()
    PaymentTransaction.objects.all().delete()
    # پرداخت‌های هزینه FK محافظت‌شده (PROTECT) به Payment دارند — قبل از Payment پاک شوند.
    # ExpenseCharge و InvestorMovement هم دادهٔ عملیاتی‌اند و با ریست پاک می‌شوند
    # (تعاریف: ExpenseCategory / RecurringExpense / Investor محفوظ می‌مانند).
    from apps.expenses.models import ExpenseChargePayment, ExpenseCharge, InvestorMovement
    report["پرداخت‌های هزینه"] = ExpenseChargePayment.objects.count()
    ExpenseChargePayment.objects.all().delete()
    report["هزینه‌های ماهانه"] = ExpenseCharge.objects.count()
    ExpenseCharge.objects.all().delete()
    report["گردش‌های سرمایه"] = InvestorMovement.objects.count()
    InvestorMovement.objects.all().delete()
    # سبدهای خرید (عادی و استعلامی) هم دادهٔ عملیاتی‌اند و با ریست پاک می‌شوند
    CartItem.objects.all().delete()
    Cart.objects.all().delete()
    InquiryCartItem.objects.all().delete()
    InquiryCart.objects.all().delete()
    from apps.accounting.models import ReturnInvoice, ReturnItem
    report["اسناد برگشت"] = ReturnInvoice.objects.count()
    ReturnItem.objects.all().delete()
    ReturnInvoice.objects.all().delete()
    ExtraCost.objects.all().delete()
    PurchaseItem.objects.all().delete()
    PurchaseInvoice.objects.all().delete()
    SalePayment.objects.all().delete()
    SaleItem.objects.all().delete()
    SaleInvoice.objects.all().delete()
    Payment.objects.all().delete()
    PaymentLog.objects.all().delete()
    StockReservation.objects.all().delete()
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    StockTransfer.objects.all().delete()
    StockMovement.objects.all().delete()
    n_ws = WarehouseStock.objects.count()
    WarehouseStock.objects.all().update(quantity=0)
    report["موجودی انبارها صفر شد"] = n_ws
    n_v = ProductVariant.objects.count()
    ProductVariant.objects.all().update(stock_quantity=0, reserved_qty=0)
    report["موجودی variantها صفر شد"] = n_v
    # مانده اول دوره طرف حساب‌ها هم صفر می‌شود
    from apps.accounting.models import Contact
    n_c = Contact.objects.count()
    Contact.objects.all().update(opening_balance_irr=0, opening_balance_cny=0)
    report["مانده اول دوره طرف حساب‌ها صفر شد"] = n_c
    # موجودی اولیه حساب‌های بانکی/صندوق هم صفر می‌شود (تراکنش‌ها که حذف شدند)
    from apps.accounting.models import Account
    n_a = Account.objects.count()
    Account.objects.all().update(initial_balance=0)
    report["موجودی بانک‌ها صفر شد"] = n_a
    return report


@transaction.atomic
def _hard_reset():
    report = _soft_reset()
    from apps.accounting.models import Contact, Account
    # سرمایه‌گذاران FK محافظت‌شده (PROTECT) به طرف حساب دارند — قبل از Contact پاک شوند.
    from apps.expenses.models import Investor
    report["سرمایه‌گذاران"] = Investor.objects.count()
    Investor.objects.all().delete()
    report["طرف حساب‌ها"] = Contact.objects.count()
    Contact.objects.all().delete()
    report["حساب‌های بانکی"] = Account.objects.count()
    Account.objects.all().delete()
    try:
        from apps.catalog.models import (
            Product, ProductImage, ProductVariant, Category, Package, PackageItem,
        )
        try:
            from apps.catalog.models import ProductPriceHistory
            ProductPriceHistory.objects.all().delete()
        except ImportError: pass
        PackageItem.objects.all().delete()
        report["پکیج‌ها"] = Package.objects.count()
        Package.objects.all().delete()
        # موجودی انبارها FK محافظت‌شده (PROTECT) به variant دارد — قبل از variant پاک شود.
        from apps.inventory.models import WarehouseStock
        WarehouseStock.objects.all().delete()
        ProductImage.objects.all().delete()
        report["variantها"] = ProductVariant.objects.count()
        ProductVariant.objects.all().delete()
        report["محصولات"] = Product.objects.count()
        Product.objects.all().delete()
        report["دسته‌بندی‌ها"] = Category.objects.count()
        Category.objects.all().delete()
    except Exception as exc:
        logger.warning(f"[HARD RESET] محصولات: {exc}")
    try:
        from apps.users.models import User
        non_super = User.objects.filter(is_superuser=False)
        report["کاربران (غیر superuser)"] = non_super.count()
        non_super.delete()
    except Exception as exc:
        logger.warning(f"[HARD RESET] کاربران: {exc}")
    return report


@method_decorator(staff_member_required, name='dispatch')
class SystemResetPageView(View):
    def get(self, request):
        return HttpResponse(self._render(request))

    def post(self, request):
        if not request.user.is_superuser:
            return HttpResponse(self._render(request, error="فقط superuser"))
        mode = request.POST.get('mode', '')
        confirm = request.POST.get('confirm', '')
        if confirm.strip() != 'YES':
            return HttpResponse(self._render(request, error="باید YES تایپ کنید"))

        # ── Safety backup قبل از ریست ──
        safety_log_id = None
        safety_msg = ""
        try:
            from .backup_tools import safety_backup_now
            sl = safety_backup_now(user=request.user, reason=f"قبل از {mode} reset")
            if sl:
                safety_log_id = sl.id
                safety_msg = f"🛡 یک safety backup گرفته شد (#{sl.id}, {sl.file_size_mb}MB)"
                logger.warning(f"[RESET] safety backup created: {sl.file_path}")
        except Exception as e:
            logger.warning(f"[RESET] safety backup خطا: {e}")
            safety_msg = f"⚠️ safety backup با خطا مواجه شد: {e}"

        try:
            if mode == 'soft':
                report = _soft_reset()
                msg = "✅ موجودی و تراکنش‌ها صفر شد"
            elif mode == 'hard':
                report = _hard_reset()
                msg = "✅ ریست کامل انجام شد"
            else:
                return HttpResponse(self._render(request, error="حالت نامعتبر"))

            logger.warning(f"[RESET] {mode.upper()} توسط {request.user} — {report}")
            return HttpResponse(self._render(request, result={
                "mode": mode, "msg": msg, "report": report, "safety_msg": safety_msg,
            }))
        except Exception as e:
            logger.exception(f"[RESET] خطا: {e}")
            return HttpResponse(self._render(request, error=f"خطا: {e}"))

    def _render(self, request, result=None, error=None):
        csrf = get_token(request)
        u = request.user
        username = (u.get_full_name() if hasattr(u, 'get_full_name') else None) or getattr(u, 'phone', None) or str(u)
        is_super = u.is_superuser
        super_note = "✓ superuser" if is_super else "⚠️ غیر superuser"
        super_color = "#28a745" if is_super else "#dc3545"
        disabled = "" if is_super else "disabled"

        result_html = ""
        if result:
            items = "".join([f"<li><b>{k}:</b> {v}</li>" for k, v in result["report"].items()])
            safety_html = f'<div style="margin-top:10px;color:#0d47a1;background:#e3f2fd;padding:8px 12px;border-radius:6px;font-size:13px;">{result.get("safety_msg", "")}</div>' if result.get("safety_msg") else ""
            result_html = f"""
            <div style="background:#d4edda;border:1px solid #28a745;border-radius:8px;padding:16px;margin-bottom:24px;color:#155724;">
              <h3 style="margin:0 0 8px;font-size:16px;">{result['msg']}</h3>
              <ul style="margin:0;padding-right:20px;font-size:13px;">{items}</ul>
              {safety_html}
            </div>"""

        error_html = ""
        if error:
            error_html = f"""<div style="background:#f8d7da;border:1px solid #dc3545;border-radius:8px;padding:16px;margin-bottom:24px;color:#721c24;"><strong>{error}</strong></div>"""

        return f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>ریست سیستم</title>
<style>
  body {{ font-family:Tahoma,sans-serif; background:#f5f6fa; margin:0; padding:24px; color:#333; }}
  .container {{ max-width:800px; margin:0 auto; }}
  .header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:24px; }}
  h1 {{ color:#2c3e50; margin:0; font-size:24px; }}
  .back-btn {{ background:#6c757d; color:#fff; text-decoration:none; padding:8px 16px; border-radius:6px; font-size:13px; }}
  .user-info {{ background:#fff; border-radius:8px; padding:12px 16px; margin-bottom:24px; font-size:14px; }}
  .super-note {{ color:{super_color}; font-weight:bold; }}
  .safety-note {{ background:#e3f2fd; padding:12px 16px; border-radius:8px; margin-bottom:20px; font-size:13px; color:#0d47a1; }}
  .card {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); border-right:5px solid; }}
  .soft {{ border-right-color:#ffc107; }}
  .hard {{ border-right-color:#dc3545; }}
  .card h2 {{ margin:0 0 12px; font-size:18px; }}
  .soft h2 {{ color:#856404; }}
  .hard h2 {{ color:#721c24; }}
  .keep {{ background:#e8f5e9; padding:10px 14px; border-radius:6px; color:#2e7d32; font-size:13px; margin-top:12px; }}
  form {{ margin-top:16px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
  input[type=text] {{ padding:10px 14px; border:1px solid #ddd; border-radius:6px; font-size:14px; width:220px; }}
  button {{ padding:10px 24px; border-radius:6px; border:none; cursor:pointer; color:#fff; font-weight:bold; }}
  button:disabled {{ opacity:0.4; cursor:not-allowed; }}
  .btn-soft {{ background:#f0ad4e; }}
  .btn-hard {{ background:#dc3545; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🗑 ریست سیستم</h1>
    <a href="/admin/" class="back-btn">← Django Admin</a>
  </div>
  <div class="user-info">کاربر: <b>{username}</b> | <span class="super-note">{super_note}</span></div>

  <div class="safety-note">
    🛡 <b>محافظت خودکار:</b> قبل از هر ریست، یک «safety backup» خودکار گرفته می‌شود و به ایمیل/تلگرام ارسال می‌شود
    (اگر در صفحه بک‌اپ فعال باشد). در صورت ضرورت می‌توانید برگردید.
  </div>

  {error_html}
  {result_html}

  <div class="card soft">
    <h2>حالت ۱ — صفر کردن موجودی و مانده‌ها</h2>
    <p>تراکنش‌ها حذف، موجودی صفر، مانده اشخاص صفر.</p>
    <div class="keep"><b>محفوظ:</b> طرف حساب‌ها، حساب‌های بانکی، محصولات، کاربران، انبارها</div>
    <form method="post" onsubmit="return confirm('مطمئنید؟');">
      <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
      <input type="hidden" name="mode" value="soft">
      <input type="text" name="confirm" placeholder="تایپ کنید: YES" required {disabled}>
      <button type="submit" class="btn-soft" {disabled}>صفر کردن موجودی</button>
    </form>
  </div>

  <div class="card hard">
    <h2>⚠️ حالت ۲ — ریست کامل</h2>
    <p>همه چیز پاک، سایت مثل روز اول.</p>
    <div class="keep"><b>محفوظ:</b> superuser ها، انبارها، SEO، نرخ ارز</div>
    <form method="post" onsubmit="return confirm('⚠️ غیر قابل بازگشت!');">
      <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
      <input type="hidden" name="mode" value="hard">
      <input type="text" name="confirm" placeholder="تایپ کنید: YES" required {disabled}>
      <button type="submit" class="btn-hard" {disabled}>ریست کامل</button>
    </form>
  </div>
</div>
</body>
</html>
        """
