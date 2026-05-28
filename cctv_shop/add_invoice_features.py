import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# ─── 1. اضافه کردن Quick Contact Modal و PDF به imports ───────
if 'useRef' not in content:
    content = content.replace(
        "import React, { useState }",
        "import React, { useState, useRef }"
    )

# ─── 2. اضافه کردن Quick Contact Creator به ThirdPartyPicker ──
old_picker = """function ThirdPartyPicker({ value, onChange }) {
  const [search, setSearch] = React.useState('')
  const [open, setOpen] = React.useState(false)
  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-all'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })
  const filtered = contacts.filter(c => !search || c.name.includes(search)).slice(0, 20)
  const selected = contacts.find(c => String(c.id) === String(value))
  return (
    <div className="relative">
      <div className="input text-xs cursor-pointer flex items-center justify-between"
        onClick={() => setOpen(o => !o)}>
        <span className={selected ? 'text-white' : 'text-gray-steel'}>
          {selected ? selected.name : 'انتخاب طرف حساب...'}
        </span>"""

new_picker = """// ─── Quick Contact Creator Modal ────────────────────────────
function QuickContactModal({ onClose, onCreated }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ name: '', contact_type: 'customer', phone: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleCreate() {
    if (!form.name.trim()) { setError('نام الزامی است'); return }
    setLoading(true)
    try {
      const res = await api.post('/accounting/contacts/', form)
      qc.invalidateQueries(['contacts-all'])
      onCreated(res.data)
      onClose()
    } catch(e) {
      setError(e.response?.data?.error || 'خطا در ایجاد')
    }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white">➕ طرف حساب جدید</h3>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-xl">×</button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="label text-xs mb-1 block">نام *</label>
            <input value={form.name} onChange={e => setForm(f=>({...f,name:e.target.value}))}
              className="input text-sm" placeholder="نام کامل یا شرکت" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">نوع</label>
            <select value={form.contact_type} onChange={e => setForm(f=>({...f,contact_type:e.target.value}))}
              className="input text-sm">
              <option value="customer">مشتری</option>
              <option value="supplier">تامین‌کننده</option>
              <option value="other">سایر</option>
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">تلفن</label>
            <input value={form.phone} onChange={e => setForm(f=>({...f,phone:e.target.value}))}
              className="input text-sm" placeholder="اختیاری" dir="ltr" />
          </div>
        </div>
        {error && <div className="text-red-400 text-xs mt-2">{error}</div>}
        <div className="flex gap-2 mt-4">
          <button onClick={handleCreate} disabled={loading}
            className="btn-primary flex-1 py-2 text-sm disabled:opacity-50">
            {loading ? 'در حال ذخیره...' : '✓ ایجاد'}
          </button>
          <button onClick={onClose} className="btn-secondary px-4 py-2 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

function ThirdPartyPicker({ value, onChange }) {
  const [search, setSearch] = React.useState('')
  const [open, setOpen] = React.useState(false)
  const [showQuickAdd, setShowQuickAdd] = React.useState(false)
  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-all'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })
  const filtered = contacts.filter(c => !search || c.name.includes(search)).slice(0, 20)
  const selected = contacts.find(c => String(c.id) === String(value))
  return (
    <div className="relative">
      {showQuickAdd && (
        <QuickContactModal
          onClose={() => setShowQuickAdd(false)}
          onCreated={(c) => { onChange(c.id); setOpen(false) }}
        />
      )}
      <div className="input text-xs cursor-pointer flex items-center justify-between"
        onClick={() => setOpen(o => !o)}>
        <span className={selected ? 'text-white' : 'text-gray-steel'}>
          {selected ? selected.name : 'انتخاب طرف حساب...'}
        </span>"""

if old_picker in content:
    content = content.replace(old_picker, new_picker)
    print("✓ QuickContactModal اضافه شد")
else:
    print("✗ ThirdPartyPicker پیدا نشد")

# اضافه کردن دکمه + به dropdown
old_search_box = """      {open && (
        <div className="absolute top-full mt-1 w-full z-50 glass-dark rounded-xl border border-white/10 shadow-2xl overflow-hidden">
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="جستجو..." className="w-full bg-transparent px-3 py-2 text-xs text-white border-b border-white/10 outline-none" />"""

new_search_box = """      {open && (
        <div className="absolute top-full mt-1 w-full z-50 glass-dark rounded-xl border border-white/10 shadow-2xl overflow-hidden">
          <div className="flex items-center border-b border-white/10">
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="جستجو..." className="flex-1 bg-transparent px-3 py-2 text-xs text-white outline-none" />
            <button onClick={(e) => { e.stopPropagation(); setOpen(false); setShowQuickAdd(true) }}
              className="px-3 py-2 text-brand hover:text-brand/80 text-xs font-bold border-r border-white/10"
              title="اضافه کردن طرف حساب جدید">
              + جدید
            </button>
          </div>"""

if old_search_box in content:
    content = content.replace(old_search_box, new_search_box)
    print("✓ دکمه + جدید اضافه شد")
else:
    print("✗ search box پیدا نشد")

# ─── 3. اضافه کردن دکمه‌های PDF/Print به InvoiceDetail ────────
# پیدا کردن InvoiceDetail
pdf_print_buttons = """
// ─── PDF / Print Export ──────────────────────────────────────
function InvoicePrintExport({ invoiceRef, invoiceNumber }) {
  function handlePrint() {
    const content = invoiceRef.current
    if (!content) return
    const win = window.open('', '_blank')
    win.document.write(`
      <html dir="rtl">
      <head>
        <meta charset="utf-8">
        <title>فاکتور ${invoiceNumber}</title>
        <style>
          body { font-family: Tahoma, Arial, sans-serif; direction: rtl; padding: 20px; color: #000; }
          table { width: 100%; border-collapse: collapse; }
          th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
          th { background: #f5f5f5; }
          @media print { .no-print { display: none; } }
        </style>
      </head>
      <body>${content.innerHTML}</body>
      </html>
    `)
    win.document.close()
    win.focus()
    setTimeout(() => { win.print(); win.close() }, 300)
  }

  async function handlePDF() {
    const { default: html2canvas } = await import('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js')
    const canvas = await html2canvas(invoiceRef.current, { scale: 2, useCORS: true })
    const imgData = canvas.toDataURL('image/jpeg', 0.95)

    // دانلود JPG
    const link = document.createElement('a')
    link.download = `invoice-${invoiceNumber}.jpg`
    link.href = imgData
    link.click()
  }

  async function handlePDFExport() {
    try {
      const { default: html2canvas } = await import('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js')
      const canvas = await html2canvas(invoiceRef.current, { scale: 2, useCORS: true })
      const imgData = canvas.toDataURL('image/png')
      const img = new Image()
      img.src = imgData
      const win = window.open('', '_blank')
      win.document.write(`<html><body style="margin:0"><img src="${imgData}" style="width:100%"></body></html>`)
      win.document.close()
      win.focus()
      setTimeout(() => { win.print() }, 500)
    } catch(e) {
      alert('خطا در ایجاد PDF')
    }
  }

  return (
    <div className="flex gap-2">
      <button onClick={handlePrint}
        className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs transition-all">
        🖨️ پرینت
      </button>
      <button onClick={handlePDF}
        className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 text-xs transition-all">
        🖼️ JPG
      </button>
      <button onClick={handlePDFExport}
        className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs transition-all">
        📄 PDF
      </button>
    </div>
  )
}

"""

# اضافه کردن قبل از export default
if 'InvoicePrintExport' not in content:
    content = content.replace(
        'export default function SaleInvoicePage',
        pdf_print_buttons + 'export default function SaleInvoicePage'
    )
    print("✓ InvoicePrintExport اضافه شد")

# پیدا کردن InvoiceDetail و اضافه کردن ref و دکمه‌ها
if 'invoiceRef' not in content:
    content = content.replace(
        'function InvoiceDetail({ id, onClose',
        'function InvoiceDetail({ id, onClose'
    )
    # اضافه کردن useRef به InvoiceDetail
    old_invoice_detail = 'function InvoiceDetail({ id, onClose, autoOpenPayment = false }) {'
    new_invoice_detail = 'function InvoiceDetail({ id, onClose, autoOpenPayment = false }) {\n  const invoiceRef = useRef(null)'
    if old_invoice_detail in content:
        content = content.replace(old_invoice_detail, new_invoice_detail)
        print("✓ invoiceRef به InvoiceDetail اضافه شد")

    # اضافه کردن دکمه‌ها بعد از دکمه بستن
    old_close_btn = '      <button onClick={onClose} className="btn-secondary text-sm px-4 py-2">بستن</button>'
    new_close_btn = '      <InvoicePrintExport invoiceRef={invoiceRef} invoiceNumber={invoice?.invoice_number || id} />\n      <button onClick={onClose} className="btn-secondary text-sm px-4 py-2">بستن</button>'
    if old_close_btn in content:
        content = content.replace(old_close_btn, new_close_btn)
        print("✓ دکمه‌های print/PDF اضافه شدند")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("\n✓ SaleInvoicePage.jsx آپدیت شد")
