import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import AmountInput from '../ui/AmountInput'

// ─── مودال افزودن طرف حساب ─────────────────────────────────────
// هم در صفحه طرف حساب‌ها (contacts_create) و هم داخل فاکتور فروش
// (forInvoice — ساخت Contact + کاربر سایه برای اتصال فاکتور) استفاده می‌شود.
// نوع‌های قابل انتخاب در فرم — چهار گروه اصلی
const FORM_TYPES = [
  ['partner',     'همکار'],
  ['customer',    'مشتری عمومی'],
  ['supplier_cn', 'تامین کننده'],
  ['shipping_co', 'حمل و ترخیص'],
  ['staff',       'پرسنل'],
]
const PARTNER_TIERS = [
  ['silver',   'همکار سیلور'],
  ['gold',     'همکار گلد'],
  ['platinum', 'همکار پلاتینیوم'],
]

export default function AddContactModal({ creatableTypes = null, onClose, onCreated, forInvoice = false }) {
  const qc = useQueryClient()
  // creatableTypes: null = بدون محدودیت (سوپریوزر) | [] = ساخت هیچ نوعی مجاز نیست
  const visibleTypes = creatableTypes === null
    ? FORM_TYPES
    : FORM_TYPES.filter(([k]) => creatableTypes.includes(k))
  // پیش‌فرض نوع: در فاکتور فروش «همکار» (اگر مجاز باشد)، در غیر این صورت اولین نوع قابل انتخاب
  const defaultType = forInvoice
    ? (visibleTypes.some(([k]) => k === 'partner') ? 'partner' : visibleTypes[0]?.[0] || 'customer')
    : (visibleTypes[0]?.[0] || 'supplier_cn')
  const emptyForm = {
    name: '', contact_type: defaultType,
    partner_tier: '', currency: 'IRR',
    phone: '', wechat: '', address: '', note: '', opening_balance_irr: '', opening_balance_cny: '',
  }
  const [form, setForm] = useState(emptyForm)
  const [msg, setMsg] = useState(null)

  const createMut = useMutation({
    mutationFn: (d) => api.post(forInvoice ? '/accounting/customers/' : '/accounting/contacts/', d).then(r => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries(['contacts-all'])
      if (forInvoice) {
        // از فاکتور فروش — طرف حساب ساخته شد و کاربر سایه برای فاکتور برمی‌گردد
        qc.invalidateQueries(['customer-search'])
        onCreated?.({ id: data.id, name: data.name, phone: data.phone || '', tier: data.tier || 'public' })
        return
      }
      setMsg({ type: 'success', text: 'طرف حساب اضافه شد' })
      setForm(emptyForm)
      setTimeout(() => { setMsg(null); onClose() }, 1200)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  // نقش کاربر مجاز به ساخت هیچ نوع طرف حسابی نیست
  if (visibleTypes.length === 0) {
    return (
      <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4">
        <div className="card p-6 w-full max-w-md text-center">
          <div className="text-3xl mb-3">🔒</div>
          <div className="text-sm text-white font-bold mb-2">ساخت طرف حساب جدید برای نقش شما مجاز نیست</div>
          <p className="text-xs text-gray-steel mb-4">فقط گروه‌های مجاز می‌توانند طرف حساب جدید بسازند.</p>
          <button onClick={onClose} className="btn-secondary text-sm px-6 py-2">بستن</button>
        </div>
      </div>
    )
  }

  const submit = () => {
    if (!form.name.trim()) {
      setMsg({ type: 'error', text: 'نام الزامی است' })
      return
    }
    // برای فاکتور فروش موبایل معتبر لازم است (کاربر سایه با آن ساخته می‌شود)
    if (forInvoice ? !/^09\d{9}$/.test(form.phone.trim()) : !form.phone.trim()) {
      setMsg({ type: 'error', text: forInvoice ? 'شماره موبایل معتبر نیست (مثال: 09123456789)' : 'موبایل الزامی است' })
      return
    }
    if (form.contact_type === 'partner' && !form.partner_tier) {
      setMsg({ type: 'error', text: 'سطح همکار را انتخاب کنید' })
      return
    }
    setMsg(null)
    createMut.mutate(form)
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">افزودن طرف حساب</h2>
            {forInvoice && <p className="text-xs text-gray-steel mt-0.5">در کاردکس اشخاص ثبت می‌شود</p>}
          </div>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="label text-xs mb-1 block">نام *</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="input text-sm" placeholder="نام طرف حساب" autoFocus />
          </div>
          <div>
            <label className="label text-xs mb-1 block">نوع *</label>
            <select value={form.contact_type}
              onChange={e => setForm(f => ({ ...f, contact_type: e.target.value, partner_tier: '' }))}
              className="input text-sm">
              {visibleTypes.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          {/* سطح همکار — فقط وقتی نوع «همکار» انتخاب شده */}
          {form.contact_type === 'partner' && (
            <div>
              <label className="label text-xs mb-1 block">سطح همکار *</label>
              <select value={form.partner_tier} onChange={e => setForm(f => ({ ...f, partner_tier: e.target.value }))} className="input text-sm">
                <option value="">انتخاب کنید...</option>
                {PARTNER_TIERS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="label text-xs mb-1 block">ارز پیش‌فرض</label>
            <select value={form.currency} onChange={e => setForm(f => ({ ...f, currency: e.target.value }))} className="input text-sm">
              <option value="CNY">یوان چین (CNY)</option>
              <option value="IRR">ریال ایران (IRR)</option>
              <option value="USD">دلار (USD)</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label text-xs mb-1 block">موبایل *</label>
              <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className="input text-sm" placeholder="09123456789" dir="ltr" maxLength={11} />
            </div>
            <div>
              <label className="label text-xs mb-1 block">وی‌چت / واتساپ / تلفن</label>
              <input value={form.wechat} onChange={e => setForm(f => ({ ...f, wechat: e.target.value }))}
                className="input text-sm" placeholder="اختیاری" />
            </div>
          </div>
          <div>
            <label className="label text-xs mb-1 block">آدرس</label>
            <textarea value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
              className="input text-sm resize-none" rows={2} placeholder="اختیاری" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">توضیحات</label>
            <textarea value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
              className="input text-sm resize-none" rows={2} />
          </div>
          <div>
            <label className="label text-xs mb-1 block">مانده اول دوره</label>
            <div className="grid grid-cols-2 gap-3">
              <AmountInput value={form.opening_balance_irr}
                onChange={e => setForm(f => ({ ...f, opening_balance_irr: e.target.value }))}
                className="input text-sm" placeholder="ریال" />
              <AmountInput value={form.opening_balance_cny}
                onChange={e => setForm(f => ({ ...f, opening_balance_cny: e.target.value }))}
                className="input text-sm" placeholder="یوان" />
            </div>
            <div className="text-[10px] text-gray-steel mt-1">مثبت = طرف حساب به ما بدهکار | منفی = ما به او بدهکاریم</div>
          </div>
        </div>
        {msg && (
          <div className={`mt-3 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}
        <div className="flex gap-3 mt-5">
          <button onClick={submit} disabled={!form.name || createMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {createMut.isPending ? 'در حال ذخیره...' : 'ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary text-sm py-2.5 px-5">انصراف</button>
        </div>
      </div>
    </div>
  )
}
