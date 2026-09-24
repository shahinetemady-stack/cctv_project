import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import AmountInput from '../ui/AmountInput'
import { PROVINCES } from '../../constants/provinces'

// ─── مودال افزودن طرف حساب ─────────────────────────────────────
// هم در صفحه طرف حساب‌ها (contacts_create) و هم داخل فاکتور فروش
// (forInvoice — ساخت Contact + کاربر سایه برای اتصال فاکتور) استفاده می‌شود.
// چیدمان فرم دقیقاً مثل «ویرایش اطلاعات طرف حساب» (EditContactModal) است.
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
    title: '', name: '', contact_type: defaultType,
    partner_tier: '', currency: 'IRR', has_fx: false,
    phone: '', wechat: '', province: '', address: '', note: '',
    opening_balance_irr: '', opening_balance_cny: '',
    credit_limit_irr: '', legacy_purchase_total: '',
  }
  const [form, setForm] = useState(emptyForm)
  const [msg, setMsg] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

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
      // اگر فرم میزبان (مثل فاکتور خرید) طرف تازه‌ساخته را می‌خواهد، بلافاصله برگردان و ببند
      if (onCreated) { onCreated(data); onClose(); return }
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
            <h2 className="font-bold text-white text-base">افزودن طرف حساب</h2>
            {forInvoice && <p className="text-xs text-gray-steel mt-0.5">در کاردکس اشخاص ثبت می‌شود</p>}
          </div>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        {msg && (
          <div className={`rounded-lg px-4 py-2 text-xs mb-3 ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-gray-steel col-span-2">عنوان
            <select value={form.title} onChange={e => set('title', e.target.value)} className="input text-sm mt-1">
              <option value="">— بدون عنوان —</option>
              <option value="mr">آقای</option>
              <option value="mrs">خانم</option>
              <option value="company">شرکت</option>
              <option value="shop">فروشگاه</option>
            </select>
          </label>
          <label className="text-xs text-gray-steel col-span-2">نام طرف حساب *
            <input value={form.name} onChange={e => set('name', e.target.value)}
              className="input text-sm mt-1" autoFocus />
          </label>
          <label className="text-xs text-gray-steel">موبایل *
            <input value={form.phone} onChange={e => set('phone', e.target.value)}
              dir="ltr" maxLength={11} placeholder="09123456789" className="input text-sm mt-1" />
          </label>
          <label className="text-xs text-gray-steel">وی‌چت / واتساپ / تلفن
            <input value={form.wechat} onChange={e => set('wechat', e.target.value)} dir="ltr" className="input text-sm mt-1" />
          </label>
          <label className="text-xs text-gray-steel">نوع *
            <select value={form.contact_type}
              onChange={e => setForm(f => ({ ...f, contact_type: e.target.value, partner_tier: '' }))}
              className="input text-sm mt-1">
              {visibleTypes.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="text-xs text-gray-steel">ارز پیش‌فرض
            <select value={form.currency} onChange={e => set('currency', e.target.value)} className="input text-sm mt-1">
              {form.has_fx && <option value="CNY">یوان چین</option>}
              <option value="IRR">ریال ایران</option>
              <option value="USD">دلار</option>
            </select>
          </label>
          {/* عملیات ارزی — فعال بودن فیلدها و ستون‌های یوانی برای این طرف حساب */}
          <label className="flex items-start gap-2 text-xs text-gray-steel cursor-pointer col-span-2">
            <input type="checkbox" checked={!!form.has_fx}
              onChange={e => setForm(f => ({ ...f, has_fx: e.target.checked, currency: !e.target.checked && f.currency === 'CNY' ? 'IRR' : f.currency }))}
              className="accent-[#FBC02D] mt-0.5" />
            <span>💱 عملیات ارزی<span className="block text-[10px] text-gray-steel mt-0.5">این شخص کارکرد یوانی دارد — ستون‌ها و فیلدهای ارزی برایش نمایش داده می‌شود</span></span>
          </label>
          <label className="text-xs text-gray-steel">استان
            <input value={form.province} onChange={e => set('province', e.target.value)}
              list="province-options" className="input text-sm mt-1" placeholder="جستجو یا انتخاب استان..." />
            <datalist id="province-options">
              {PROVINCES.map(p => <option key={p} value={p} />)}
            </datalist>
          </label>
          <label className="text-xs text-gray-steel col-span-2">آدرس
            <textarea value={form.address} onChange={e => set('address', e.target.value)} rows={2} className="input text-sm mt-1" />
          </label>
          <label className="text-xs text-gray-steel col-span-2">توضیحات
            <textarea value={form.note} onChange={e => set('note', e.target.value)} rows={2} className="input text-sm mt-1" />
          </label>
          <label className="text-xs text-gray-steel">مانده اول دوره (ریال)
            <AmountInput value={form.opening_balance_irr}
              onChange={e => set('opening_balance_irr', e.target.value)}
              className="input text-sm mt-1" placeholder="0" />
          </label>
          {form.has_fx && (
            <label className="text-xs text-gray-steel">مانده اول دوره (یوان)
              <AmountInput value={form.opening_balance_cny}
                onChange={e => set('opening_balance_cny', e.target.value)}
                className="input text-sm mt-1" placeholder="0" />
            </label>
          )}
          <div className="col-span-2 text-[10px] text-gray-steel">مثبت = طرف حساب به ما بدهکار | منفی = ما به او بدهکاریم</div>
          {/* سقف اعتبار — شامل هر نوع بدهی: حساب باز، چک وصول‌نشده، ردیف‌های تسویه باز */}
          <label className="text-xs text-gray-steel col-span-2">سقف اعتبار (ریال) — ۰ یعنی نامحدود
            <AmountInput value={form.credit_limit_irr}
              onChange={e => set('credit_limit_irr', e.target.value)}
              className="input text-sm mt-1" placeholder="0" />
          </label>
          <div className="col-span-2 text-[10px] text-gray-steel -mt-2">
            شامل انواع بدهی می‌شود: حساب باز، چک وصول‌نشده و هر بدهی تسویه‌نشده — اگر مجموع بدهی از سقف بگذرد، فروش اعتباری جدید بسته می‌شود
          </div>
          <label className="text-xs text-gray-steel col-span-2">مجموع سابقه خرید قبلی خارج از سایت (ریال)
            <AmountInput value={form.legacy_purchase_total}
              onChange={e => set('legacy_purchase_total', e.target.value)}
              className="input text-sm mt-1" placeholder="0" />
          </label>
          <div className="col-span-2 text-[10px] text-gray-steel -mt-2">
            این مبلغ با خریدهای آنلاین سایت جمع می‌شود و ملاک ارتقای خودکار سطح همکار (باشگاه همکاران) است
          </div>
        </div>
        {/* سطح همکار — فقط وقتی نوع «همکار» انتخاب شده (مثل بخش پایین فرم ویرایش) */}
        {form.contact_type === 'partner' && (
          <div className="mt-4 pt-4 border-t border-white/10 space-y-3">
            <label className="text-xs text-gray-steel block">سطح همکار *
              <select value={form.partner_tier} onChange={e => set('partner_tier', e.target.value)} className="input text-xs mt-1">
                <option value="">انتخاب کنید...</option>
                {PARTNER_TIERS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
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
