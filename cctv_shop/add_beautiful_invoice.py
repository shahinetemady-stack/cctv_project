import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# ─── 1. اضافه کردن کامپوننت فاکتور زیبا ─────────────────────
beautiful_invoice = '''
// ─── فاکتور زیبا برای پرینت ──────────────────────────────────
function InvoicePrintView({ inv, onClose }) {
  const settings_data = {
    site_name: document.title || 'فروشگاه قطعات دوربین',
  }

  function handlePrint() {
    window.print()
  }

  const totalItems = inv.items?.reduce((s, i) => s + i.quantity, 0) || 0
  const totalAmount = inv.total_amount || 0
  const paidAmount = inv.paid_amount || 0
  const remaining = totalAmount - paidAmount

  return (
    <>
      {/* استایل پرینت */}
      <style>{`
        @media print {
          body > * { display: none !important; }
          .invoice-modal { display: block !important; position: fixed; inset: 0; background: white; z-index: 9999; }
          .no-print { display: none !important; }
          .invoice-print-area { padding: 20px; }
        }
      `}</style>

      <div className="invoice-modal fixed inset-0 z-[200] bg-white overflow-auto">
        {/* دکمه‌های کنترل */}
        <div className="no-print flex items-center gap-3 p-4 bg-gray-100 border-b sticky top-0">
          <button onClick={handlePrint}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg font-semibold text-sm hover:bg-blue-700">
            🖨️ پرینت / PDF
          </button>
          <button onClick={onClose}
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-600 text-white rounded-lg font-semibold text-sm hover:bg-gray-700">
            ✕ بستن
          </button>
          <span className="text-gray-500 text-xs">برای ذخیره PDF: در پنجره پرینت «Save as PDF» را انتخاب کنید</span>
        </div>

        {/* محتوای فاکتور */}
        <div className="invoice-print-area max-w-3xl mx-auto p-8" dir="rtl"
          style={{fontFamily: 'Tahoma, Arial, sans-serif', color: '#1a1a1a'}}>

          {/* هدر */}
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:32, paddingBottom:20, borderBottom:'3px solid #1a56db'}}>
            <div>
              <div style={{fontSize:28, fontWeight:'bold', color:'#1a56db', marginBottom:4}}>فاکتور فروش</div>
              <div style={{fontSize:13, color:'#555'}}>بازرگانی دوربینکار</div>
              <div style={{fontSize:12, color:'#777', marginTop:4}}>تهران - خیابان جمهوری</div>
            </div>
            <div style={{textAlign:'left', background:'#f0f4ff', padding:16, borderRadius:12}}>
              <div style={{fontSize:13, color:'#555', marginBottom:4}}>شماره فاکتور:</div>
              <div style={{fontSize:18, fontWeight:'bold', color:'#1a56db', marginBottom:8}}>{inv.invoice_number}</div>
              <div style={{fontSize:12, color:'#555'}}>تاریخ: {inv.date || inv.created_at?.slice(0,10)}</div>
              {inv.due_date && <div style={{fontSize:12, color:'#e53e3e', marginTop:4}}>سررسید: {inv.due_date}</div>}
            </div>
          </div>

          {/* اطلاعات طرفین */}
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginBottom:28}}>
            <div style={{background:'#f8fafc', padding:16, borderRadius:10, border:'1px solid #e2e8f0'}}>
              <div style={{fontSize:11, color:'#888', marginBottom:8, fontWeight:'bold'}}>فروشنده:</div>
              <div style={{fontSize:14, fontWeight:'bold', color:'#1a1a1a'}}>بازرگانی دوربینکار</div>
              <div style={{fontSize:12, color:'#555', marginTop:4}}>تلفن: ۰۲۱-۶۶۷۶۴۰۰۳</div>
            </div>
            <div style={{background:'#f8fafc', padding:16, borderRadius:10, border:'1px solid #e2e8f0'}}>
              <div style={{fontSize:11, color:'#888', marginBottom:8, fontWeight:'bold'}}>خریدار:</div>
              <div style={{fontSize:14, fontWeight:'bold', color:'#1a1a1a'}}>{inv.contact_name || '—'}</div>
              {inv.contact_phone && <div style={{fontSize:12, color:'#555', marginTop:4}}>تلفن: {inv.contact_phone}</div>}
            </div>
          </div>

          {/* جدول اقلام */}
          <table style={{width:'100%', borderCollapse:'collapse', marginBottom:24}}>
            <thead>
              <tr style={{background:'#1a56db', color:'white'}}>
                {['ردیف','شرح کالا','تعداد','قیمت واحد (ت)','تخفیف','مبلغ (ت)'].map(h => (
                  <th key={h} style={{padding:'10px 12px', textAlign:'right', fontSize:12, fontWeight:'bold'}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inv.items?.map((item, idx) => (
                <tr key={idx} style={{background: idx%2===0?'#fff':'#f8fafc', borderBottom:'1px solid #e2e8f0'}}>
                  <td style={{padding:'10px 12px', fontSize:12, textAlign:'center'}}>{idx+1}</td>
                  <td style={{padding:'10px 12px', fontSize:12}}>{item.variant_name || item.product_name}</td>
                  <td style={{padding:'10px 12px', fontSize:12, textAlign:'center'}}>{Number(item.quantity).toLocaleString('fa-IR')}</td>
                  <td style={{padding:'10px 12px', fontSize:12, textAlign:'left'}}>{Number(item.unit_price||0).toLocaleString('fa-IR')}</td>
                  <td style={{padding:'10px 12px', fontSize:12, textAlign:'center'}}>{item.discount_percent ? item.discount_percent+'%' : '—'}</td>
                  <td style={{padding:'10px 12px', fontSize:12, textAlign:'left', fontWeight:'bold'}}>{Number(item.total_price||item.unit_price*item.quantity||0).toLocaleString('fa-IR')}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* جمع‌بندی */}
          <div style={{display:'flex', justifyContent:'flex-end', marginBottom:32}}>
            <div style={{width:280, background:'#f8fafc', borderRadius:12, padding:16, border:'1px solid #e2e8f0'}}>
              <div style={{display:'flex', justifyContent:'space-between', marginBottom:8, fontSize:13}}>
                <span style={{color:'#555'}}>جمع کل:</span>
                <span style={{fontWeight:'bold'}}>{Number(totalAmount).toLocaleString('fa-IR')} ت</span>
              </div>
              {paidAmount > 0 && (
                <div style={{display:'flex', justifyContent:'space-between', marginBottom:8, fontSize:13}}>
                  <span style={{color:'#22c55e'}}>پرداخت شده:</span>
                  <span style={{fontWeight:'bold', color:'#22c55e'}}>{Number(paidAmount).toLocaleString('fa-IR')} ت</span>
                </div>
              )}
              {remaining > 0 && (
                <div style={{display:'flex', justifyContent:'space-between', paddingTop:8, borderTop:'2px solid #1a56db', fontSize:15}}>
                  <span style={{color:'#e53e3e', fontWeight:'bold'}}>مانده:</span>
                  <span style={{fontWeight:'bold', color:'#e53e3e'}}>{Number(remaining).toLocaleString('fa-IR')} ت</span>
                </div>
              )}
              {remaining === 0 && (
                <div style={{textAlign:'center', paddingTop:8, borderTop:'2px solid #22c55e', color:'#22c55e', fontWeight:'bold', fontSize:14}}>
                  ✓ تسویه شده
                </div>
              )}
            </div>
          </div>

          {/* یادداشت */}
          {inv.notes && (
            <div style={{background:'#fffbeb', border:'1px solid #f59e0b', borderRadius:8, padding:12, marginBottom:24}}>
              <div style={{fontSize:11, color:'#92400e', fontWeight:'bold', marginBottom:4}}>یادداشت:</div>
              <div style={{fontSize:12, color:'#78350f'}}>{inv.notes}</div>
            </div>
          )}

          {/* امضا */}
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:40, marginTop:48}}>
            <div style={{textAlign:'center'}}>
              <div style={{borderTop:'1px solid #ccc', paddingTop:8, fontSize:12, color:'#555'}}>مهر و امضای فروشنده</div>
            </div>
            <div style={{textAlign:'center'}}>
              <div style={{borderTop:'1px solid #ccc', paddingTop:8, fontSize:12, color:'#555'}}>مهر و امضای خریدار</div>
            </div>
          </div>

          {/* فوتر */}
          <div style={{marginTop:32, paddingTop:16, borderTop:'1px solid #e2e8f0', textAlign:'center', fontSize:11, color:'#888'}}>
            این فاکتور به صورت سیستمی صادر شده و معتبر می‌باشد | بازرگانی دوربینکار
          </div>
        </div>
      </div>
    </>
  )
}

'''

# اضافه کردن قبل از export default
if 'InvoicePrintView' not in content:
    content = content.replace(
        'export default function SaleInvoicePage',
        beautiful_invoice + 'export default function SaleInvoicePage'
    )
    print("✓ InvoicePrintView اضافه شد")

# ─── 2. اضافه کردن state برای نمایش فاکتور زیبا ──────────────
# پیدا کردن InvoiceDetail و اضافه کردن showPrint state
if 'showPrint' not in content:
    old = 'function InvoiceDetail({ id, onClose, autoOpenPayment = false }) {\n  const invoiceRef = useRef(null)'
    new = 'function InvoiceDetail({ id, onClose, autoOpenPayment = false }) {\n  const invoiceRef = useRef(null)\n  const [showPrint, setShowPrint] = useState(false)'
    if old in content:
        content = content.replace(old, new)
        print("✓ showPrint state اضافه شد")
    else:
        # بدون invoiceRef
        old2 = 'function InvoiceDetail({ id, onClose, autoOpenPayment = false }) {'
        new2 = 'function InvoiceDetail({ id, onClose, autoOpenPayment = false }) {\n  const [showPrint, setShowPrint] = useState(false)'
        if old2 in content:
            content = content.replace(old2, new2)
            print("✓ showPrint state اضافه شد (بدون invoiceRef)")

# ─── 3. جایگزینی دکمه‌های قدیمی با دکمه‌های جدید ─────────────
old_btns = """      {/* دکمه‌های خروجی */}
      <div className="flex gap-2 mt-4 pt-4 border-t border-white/10">
        <button onClick={() => window.print()}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs transition-all">
          🖨️ پرینت
        </button>
        <button onClick={() => {
          const style = document.createElement('style')
          style.innerHTML = '@media print { body * { visibility: hidden; } .invoice-print, .invoice-print * { visibility: visible; } .invoice-print { position: absolute; left: 0; top: 0; width: 100%; } }'
          document.head.appendChild(style)
          window.print()
          setTimeout(() => document.head.removeChild(style), 1000)
        }} className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs transition-all">
          📄 PDF
        </button>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand/20 hover:bg-brand/30 text-brand text-xs transition-all mr-auto">
          ✕ بستن
        </button>
      </div>"""

new_btns = """      {/* دکمه‌های خروجی */}
      <div className="flex gap-2 mt-4 pt-4 border-t border-white/10">
        <button onClick={() => setShowPrint(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 text-xs transition-all font-semibold">
          🖨️ پرینت / PDF فاکتور
        </button>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs transition-all mr-auto">
          ✕ بستن
        </button>
      </div>
      {showPrint && inv && <InvoicePrintView inv={inv} onClose={() => setShowPrint(false)} />}"""

if old_btns in content:
    content = content.replace(old_btns, new_btns)
    print("✓ دکمه‌ها جایگزین شدند")
elif 'setShowPrint' not in content:
    print("✗ دکمه‌های قدیمی پیدا نشدند")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("\n✓ SaleInvoicePage.jsx آپدیت شد")
print("Lines:", content.count('\n'))
