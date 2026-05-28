"""
python write_sale_invoice.py
فایل SaleInvoicePage.jsx را کامل و سالم می‌نویسد
"""
import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

# ─── خواندن فایل فعلی برای استخراج بخش‌های سالم ─────────────
with open(page_path, encoding='utf-8') as f:
    original = f.read()

# پیدا کردن NewInvoiceForm و SaleInvoicePage که سالم هستند
new_form_idx = original.find('// ─── فرم فاکتور جدید')
if new_form_idx < 0:
    new_form_idx = original.find('function NewInvoiceForm')

sale_page_idx = original.find('export default function SaleInvoicePage')

print(f"NewInvoiceForm at: {new_form_idx}")
print(f"SaleInvoicePage at: {sale_page_idx}")

# استخراج بخش‌های سالم
new_form_and_main = original[new_form_idx:] if new_form_idx > 0 else ""

# بخش اول فایل (imports تا قبل از InvoiceDetail)
# پیدا کردن شروع InvoiceDetail
inv_detail_idx = original.find('function InvoiceDetail(')
first_part = original[:inv_detail_idx] if inv_detail_idx > 0 else ""

print(f"First part: {len(first_part)} chars")
print(f"NewForm+Main: {len(new_form_and_main)} chars")

# ─── ساخت InvoiceDetail سالم با قابلیت پرینت ────────────────
INVOICE_DETAIL = '''
// ─── تابع پرینت فاکتور زیبا ────────────────────────────────
function printInvoice(inv) {
  const items = inv.items || []
  const total = items.reduce((s, item) => s + (Number(item.total_price) || Number(item.unit_price) * Number(item.quantity) || 0), 0)
  const paid = Number(inv.paid_amount || 0)
  const remaining = total - paid

  const win = window.open('', '_blank', 'width=900,height=700')
  win.document.write(`<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8">
<title>فاکتور ${inv.invoice_number || ''}</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:Tahoma,Arial,sans-serif; direction:rtl; color:#111; background:#fff; padding:30px; font-size:13px; }
.header { display:flex; justify-content:space-between; align-items:flex-start; border-bottom:3px solid #0055cc; padding-bottom:20px; margin-bottom:24px; }
.logo { font-size:20px; font-weight:bold; color:#0055cc; }
.logo-sub { font-size:11px; color:#666; margin-top:4px; }
.inv-meta { text-align:left; }
.inv-meta h2 { font-size:18px; color:#111; margin-bottom:8px; }
.inv-meta table td { padding:3px 10px; font-size:12px; }
.inv-meta td:first-child { color:#888; }
.inv-meta td:last-child { font-weight:bold; color:#0055cc; }
.parties { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:24px; }
.party { border:1px solid #ddd; border-radius:6px; padding:12px; }
.party h4 { font-size:10px; color:#999; margin-bottom:6px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid #f0f0f0; padding-bottom:6px; }
.party p { font-size:14px; font-weight:bold; }
.party small { font-size:11px; color:#666; }
table.items { width:100%; border-collapse:collapse; margin-bottom:24px; border-radius:8px; overflow:hidden; }
table.items thead tr { background:#0055cc; color:#fff; }
table.items th { padding:10px 12px; font-size:12px; font-weight:600; }
table.items td { padding:9px 12px; border-bottom:1px solid #f0f0f0; }
table.items tbody tr:nth-child(even) { background:#f8f9ff; }
table.items tfoot tr { background:#f0f5ff; font-weight:bold; border-top:2px solid #0055cc; }
.summary { display:flex; justify-content:flex-end; margin-bottom:24px; }
.summary table { min-width:280px; }
.summary td { padding:6px 14px; font-size:13px; }
.summary .row-total td { font-size:16px; font-weight:bold; color:#0055cc; background:#f0f5ff; }
.summary .row-paid td { color:#059669; }
.summary .row-remain td { color:#dc2626; font-weight:bold; }
.notes { background:#fffbf0; border:1px solid #fde68a; border-radius:6px; padding:12px; margin-bottom:24px; font-size:12px; }
.footer { border-top:1px solid #e5e7eb; padding-top:16px; display:flex; justify-content:space-between; align-items:center; color:#999; font-size:11px; }
.stamp { text-align:center; }
.stamp-circle { display:inline-flex; align-items:center; justify-content:center; width:90px; height:90px; border-radius:50%; border:2px dashed #ccc; color:#ccc; font-size:10px; text-align:center; }
@media print { body{padding:15px} @page{margin:1cm} }
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">🎥 ${inv.seller_name || 'فروشگاه قطعات دوربین'}</div>
    <div class="logo-sub">${inv.seller_phone || ''}</div>
    <div class="logo-sub">${inv.seller_address || ''}</div>
  </div>
  <div class="inv-meta">
    <h2>فاکتور فروش</h2>
    <table>
      <tr><td>شماره فاکتور:</td><td>${inv.invoice_number || ''}</td></tr>
      <tr><td>تاریخ:</td><td>${inv.date || ''}</td></tr>
      <tr><td>وضعیت:</td><td>${inv.status_display || ''}</td></tr>
    </table>
  </div>
</div>
<div class="parties">
  <div class="party"><h4>فروشنده</h4><p>${inv.seller_name || 'فروشگاه قطعات دوربین'}</p><small>${inv.seller_phone || ''}</small></div>
  <div class="party"><h4>خریدار</h4><p>${inv.contact_name || inv.contact || 'مشتری'}</p><small>${inv.contact_phone || ''}</small></div>
</div>
<table class="items">
  <thead><tr><th>#</th><th>نام کالا</th><th>تعداد</th><th>قیمت واحد (ت)</th><th>جمع (ت)</th></tr></thead>
  <tbody>
    ${items.map((item, idx) => {
      const lineTotal = Number(item.total_price) || (Number(item.unit_price) * Number(item.quantity)) || 0
      return \`<tr><td>\${idx+1}</td><td>\${item.variant_name || item.product_name || ''}</td><td>\${Number(item.quantity||0).toLocaleString('fa-IR')}</td><td>\${Number(item.unit_price||0).toLocaleString('fa-IR')}</td><td>\${lineTotal.toLocaleString('fa-IR')}</td></tr>\`
    }).join('')}
  </tbody>
  <tfoot><tr><td colspan="4" style="text-align:left">جمع کل</td><td>${total.toLocaleString('fa-IR')} تومان</td></tr></tfoot>
</table>
<div class="summary">
  <table>
    <tr class="row-total"><td>جمع کل:</td><td>${total.toLocaleString('fa-IR')} تومان</td></tr>
    ${paid > 0 ? `<tr class="row-paid"><td>پرداخت شده:</td><td>${paid.toLocaleString('fa-IR')} تومان</td></tr>` : ''}
    ${remaining > 0 ? `<tr class="row-remain"><td>مانده بدهی:</td><td>${remaining.toLocaleString('fa-IR')} تومان</td></tr>` : ''}
  </table>
</div>
${inv.note ? `<div class="notes"><strong>توضیحات:</strong> ${inv.note}</div>` : ''}
<div class="footer">
  <span>این فاکتور رایانه‌ای است و نیازی به مهر ندارد</span>
  <div class="stamp"><div class="stamp-circle">مهر<br>و<br>امضا</div></div>
  <span>${inv.seller_name || ''}</span>
</div>
</body></html>`)
  win.document.close()
  win.focus()
  setTimeout(() => win.print(), 500)
}

// ─── Quick Add Contact Modal ──────────────────────────────────
function QuickAddContact({ onClose, onCreated }) {
  const [form, setForm] = React.useState({ name: '', contact_type: 'customer', phone: '' })
  const [loading, setLoading] = React.useState(false)
  const [err, setErr] = React.useState('')
  const qc = useQueryClient()

  async function save() {
    if (!form.name.trim()) { setErr('نام الزامی است'); return }
    setLoading(true)
    try {
      const res = await api.post('/accounting/contacts/', form)
      qc.invalidateQueries(['contacts-all'])
      onCreated(res.data)
    } catch(e) {
      setErr(e.response?.data?.error || 'خطا')
    }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-4">
      <div className="card p-6 w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white text-sm">➕ افزودن طرف حساب جدید</h3>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-xl">×</button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="label text-xs mb-1 block">نام *</label>
            <input value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))}
              className="input text-sm" placeholder="نام کامل یا شرکت" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">نوع</label>
            <select value={form.contact_type}
              onChange={e => setForm(f => ({...f, contact_type: e.target.value}))}
              className="input text-sm">
              <option value="customer">مشتری</option>
              <option value="supplier">تامین‌کننده</option>
              <option value="other">سایر</option>
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">تلفن</label>
            <input value={form.phone} onChange={e => setForm(f => ({...f, phone: e.target.value}))}
              className="input text-sm" placeholder="اختیاری" dir="ltr" />
          </div>
        </div>
        {err && <div className="text-red-400 text-xs mt-2">{err}</div>}
        <div className="flex gap-2 mt-4">
          <button onClick={save} disabled={loading}
            className="btn-primary flex-1 py-2 text-sm disabled:opacity-50">
            {loading ? '...' : '✓ ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary px-4 py-2 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

'''

# ساختن فایل نهایی
final = first_part + INVOICE_DETAIL

# خواندن InvoiceDetail اصلی از فایل برای بازیابی پرداخت‌ها
# پیدا کردن بخش پرداخت‌ها
inv_end = original.find('// ─── فرم فاکتور جدید')
if inv_end < 0:
    inv_end = original.find('function NewInvoiceForm')

if inv_detail_idx > 0 and inv_end > inv_detail_idx:
    original_detail = original[inv_detail_idx:inv_end]
    # پیدا کردن بخش پرداخت در InvoiceDetail اصلی
    pay_idx = original_detail.find('// ─── بخش پرداخت')
    if pay_idx < 0:
        pay_idx = original_detail.find('payForm')
    if pay_idx > 0:
        print(f"Payment section found at {pay_idx} in InvoiceDetail")

# اضافه کردن InvoiceDetail با پرینت
invoice_detail_clean = '''
function InvoiceDetail({ id, onClose, autoOpenPayment = false }) {
  const [payForm, setPayForm] = React.useState({ show: false, amount: '', method: 'cash', to_account_id: '', reference: '', due_date: '', third_party_id: '' })
  const [msg, setMsg] = React.useState(null)
  const qc = useQueryClient()

  const { data: inv, isLoading } = useQuery({
    queryKey: ['sale-invoice-detail', id],
    queryFn: () => api.get(`/accounting/sale-invoices/${id}/`).then(r => r.data),
  })

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-all'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const payMut = useMutation({
    mutationFn: (d) => api.post('/accounting/sale-payments/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['sale-invoice-detail', id])
      qc.invalidateQueries(['sale-invoices'])
      setPayForm(f => ({ ...f, show: false }))
      setMsg({ type: 'success', text: 'پرداخت ثبت شد' })
      setTimeout(() => setMsg(null), 2000)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  React.useEffect(() => {
    if (autoOpenPayment && inv && inv.status !== 'paid') {
      setPayForm(f => ({ ...f, show: true, amount: inv.remaining_amount || '' }))
    }
  }, [autoOpenPayment, inv])

  if (isLoading) return <div className="p-8 text-center text-gray-steel text-sm">در حال بارگذاری...</div>
  if (!inv) return <div className="p-8 text-center text-gray-steel text-sm">فاکتور یافت نشد</div>

  const STATUS = {
    draft: { bg: '#1f2937', text: '#9CA3AF', label: 'پیش‌نویس' },
    issued: { bg: '#1e3a5f', text: '#60A5FA', label: 'صادر شده' },
    paid: { bg: '#064e3b', text: '#34D399', label: 'پرداخت شده' },
    partial: { bg: '#4c1d95', text: '#A78BFA', label: 'جزئی' },
    cancelled: { bg: '#7f1d1d', text: '#F87171', label: 'لغو' },
  }
  const st = STATUS[inv.status] || STATUS.issued
  const irrAccounts = accounts.filter(a => a.currency === 'IRR')

  return (
    <div className="card p-0 overflow-hidden">
      {/* هدر */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-bold text-brand">{inv.invoice_number}</span>
          <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: st.bg, color: st.text }}>{st.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => printInvoice(inv)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand/20 hover:bg-brand/30 text-brand text-xs transition-all">
            🖨️ پرینت / PDF
          </button>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-xl px-2">×</button>
        </div>
      </div>

      {/* اطلاعات فاکتور */}
      <div className="p-4 grid grid-cols-3 gap-4 border-b border-white/10 text-xs">
        <div><span className="text-gray-steel">طرف حساب: </span><span className="text-white font-semibold">{inv.contact_name || '—'}</span></div>
        <div><span className="text-gray-steel">تاریخ: </span><span className="text-white">{inv.date}</span></div>
        <div><span className="text-gray-steel">مبلغ کل: </span><span className="text-white font-bold">{fmt(inv.total_amount)} ت</span></div>
        <div><span className="text-gray-steel">پرداخت شده: </span><span className="text-green-400 font-bold">{fmt(inv.paid_amount)} ت</span></div>
        <div><span className="text-gray-steel">مانده: </span><span className="text-red-400 font-bold">{fmt(inv.remaining_amount)} ت</span></div>
        {inv.note && <div className="col-span-3"><span className="text-gray-steel">یادداشت: </span><span className="text-white">{inv.note}</span></div>}
      </div>

      {/* اقلام */}
      <div className="p-4">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'rgba(0,102,255,0.15)', borderBottom: '1px solid rgba(0,102,255,0.3)' }}>
              {['کالا', 'تعداد', 'قیمت واحد', 'جمع'].map(h => (
                <th key={h} style={{ padding: '8px 10px', textAlign: 'right', color: '#60A5FA', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(inv.items || []).map((item, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '8px 10px', color: '#fff' }}>{item.variant_name || item.product_name}</td>
                <td style={{ padding: '8px 10px', color: '#9CA3AF' }}>{fmt(item.quantity)}</td>
                <td style={{ padding: '8px 10px', color: '#9CA3AF' }}>{fmt(item.unit_price)} ت</td>
                <td style={{ padding: '8px 10px', color: '#fff', fontWeight: 600 }}>{fmt(item.total_price)} ت</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {msg && (
        <div className={`mx-4 mb-2 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
          {msg.text}
        </div>
      )}

      {/* ثبت پرداخت */}
      {inv.status !== 'paid' && (
        <div className="p-4 border-t border-white/10">
          {!payForm.show ? (
            <button onClick={() => setPayForm(f => ({ ...f, show: true, amount: inv.remaining_amount || '' }))}
              className="btn-primary text-xs px-4 py-2">+ ثبت پرداخت</button>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label text-xs mb-1 block">مبلغ</label>
                  <input inputMode="numeric" value={payForm.amount}
                    onChange={e => setPayForm(f => ({ ...f, amount: e.target.value }))}
                    className="input text-xs" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">روش</label>
                  <select value={payForm.method}
                    onChange={e => setPayForm(f => ({ ...f, method: e.target.value }))}
                    className="input text-xs">
                    <option value="cash">نقد</option>
                    <option value="transfer">حواله</option>
                    <option value="card">کارت</option>
                    <option value="cheque">چک</option>
                    <option value="credit">نسیه</option>
                  </select>
                </div>
                {['transfer', 'card'].includes(payForm.method) && (
                  <div>
                    <label className="label text-xs mb-1 block">حساب</label>
                    <select value={payForm.to_account_id}
                      onChange={e => setPayForm(f => ({ ...f, to_account_id: e.target.value }))}
                      className="input text-xs">
                      <option value="">انتخاب...</option>
                      {irrAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                    </select>
                  </div>
                )}
                {payForm.method === 'credit' && (
                  <div>
                    <label className="label text-xs mb-1 block">سررسید</label>
                    <input type="date" value={payForm.due_date}
                      onChange={e => setPayForm(f => ({ ...f, due_date: e.target.value }))}
                      className="input text-xs" />
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    if (['transfer','card'].includes(payForm.method) && !payForm.to_account_id) return setMsg({ type: 'error', text: 'حساب را انتخاب کنید' })
                    if (payForm.method === 'credit' && !payForm.due_date) return setMsg({ type: 'error', text: 'تاریخ سررسید را وارد کنید' })
                    payMut.mutate({ invoice_id: id, ...payForm })
                  }}
                  disabled={!payForm.amount || payMut.isPending}
                  className="btn-primary text-xs px-4 py-2 disabled:opacity-50">ثبت</button>
                <button onClick={() => setPayForm(f => ({ ...f, show: false }))}
                  className="btn-secondary text-xs px-4 py-2">انصراف</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* لیست پرداخت‌ها */}
      {(inv.payments || []).length > 0 && (
        <div className="p-4 border-t border-white/10">
          <div className="text-xs font-semibold text-white mb-2">پرداخت‌های ثبت شده:</div>
          <div className="space-y-1.5">
            {inv.payments.map(p => (
              <div key={p.id} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2 text-xs">
                <div>
                  <span className="text-white">{p.method_display}</span>
                  {p.to_account && <span className="text-gray-steel"> → {p.to_account}</span>}
                  <span className="text-gray-steel mr-2">{p.date}</span>
                </div>
                <span className="text-green-400 font-bold">{fmt(p.amount)} ت</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

'''

final += invoice_detail_clean + new_form_and_main

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(final)

print(f"✓ فایل نهایی نوشته شد: {final.count(chr(10))} خط")
print("صفحه را refresh کنید")
