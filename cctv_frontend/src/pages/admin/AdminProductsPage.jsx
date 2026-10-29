import { useState, useEffect, useRef, Fragment } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Search, X, Package, Star, FileText, Upload } from 'lucide-react'
import api from '../../services/api'
import { mediaUrl } from '../../utils/media'
import { PageLoader } from '../../components/ui'
import AmountInput from '../../components/ui/AmountInput'
import CharCount from '../../components/ui/CharCount'
import StockChips from '../../components/ui/StockChips'

// ─── تعریف گروه‌های فیلد — choiceها مطابق مدل بک‌اند ──────────
const FIELD_GROUPS = [
  { title: 'اطلاعات اصلی', fields: [
    { k: 'name', l: 'نام محصول *' },
    { k: 'brand', l: 'برند', type: 'brand' },
    { k: 'model_number', l: 'شماره مدل' },
    { k: 'category', l: 'دسته‌بندی', type: 'category' },
    { k: 'short_description', l: 'توضیح کوتاه' },
    { k: 'description', l: 'توضیح کامل', type: 'textarea' },
  ]},
  { title: 'برد', fields: [
    { k: 'board_name', l: 'نام برد', hint: 'اگر خالی بماند، هنگام ذخیره از شماره مدل پر می‌شود' },
    { k: 'board_system', l: 'سیستم برد', choices: ['AHD', 'IP'] },
    { k: 'board_resolution', l: 'رزولوشن برد', choices: ['2MP', '4MP', '5MP', '8MP', '12MP'] },
    { k: 'board_dimensions', l: 'ابعاد برد', type: 'combo',
      choices: ['۳۲*۳۲', '۳۸*۳۸', '۳۸*۴۸', '۳۸*۳۸ + ۳۸*۳۸', '۳۸*۳۸ + ۶۰*۵۱'],
      hint: 'برای بردهای دو تکه (مثل پلاک‌خوان) با «+» بنویس — مثلاً ۳۸*۳۸ + ۶۰*۵۱' },
    { k: 'board_fps', l: 'نرخ فریم (FPS)', type: 'combo',
      choices: ['20fps', '25fps', '30fps'],
      hint: 'اگر با رزولوشن فرق می‌کند بنویس — مثلاً 20fps@5MP' },
    { k: 'ai_processor', l: 'پردازنده' },
    { k: 'brand', l: 'شرکت سازنده', type: 'brand' },
    { k: 'has_microphone', l: 'قابلیت نصب میکروفون داخلی', type: 'checkbox' },
  ]},
  { title: 'سنسور', fields: [
    { k: 'sensor_name', l: 'نام سنسور' },
    { k: 'sensor_size', l: 'سایز سنسور', choices: ['1/4"', '1/3"', '1/2.8"', '1/2.7"', '1/2"', '1/1.8"'] },
  ]},
  { title: 'لنز', fields: [
    { k: 'lens_degree', l: 'فاصله کانونی', type: 'combo', choices: ['1.7mm', '1.8mm', '2.8mm', '3.6mm', '4mm', '6mm', '8mm', '12mm', '16mm'],
      hint: 'برای وریفوکال/موتورایز بنویس — مثلاً 2.8-12mm' },
    { k: 'lens_resolution', l: 'رزولوشن لنز', choices: ['3MP', '5MP', '8MP'] },
    { k: 'focal_ratio', l: 'کلاس نوری لنز', choices: ['معمولی IR', 'استارلایت Starlight', 'دارکلایت Darklight'] },
    { k: 'lens_aperture', l: 'ضریب دیافراگم (Aperture)', type: 'combo', choices: ['F1.0', 'F1.2', 'F1.4', 'F1.6', 'F2.0'] },
    { k: 'lens_image_size', l: 'سایز سنسور سازگار (Image Size)', choices: ['1/2.5"', '1/2.7"', '1/2.8"', '1/2.9"', '1/3"'] },
    { k: 'lens_mount', l: 'نوع مانت / رزوه (Mount Type)', choices: ['M12', 'D14', 'CS-Mount'] },
    { k: 'lens_kit', l: 'اقلام همراه و نگهدارنده', choices: ['فقط لنز', 'لنز + هولدر ثابت', 'لنز + فیلتر IR-Cut', 'فقط هولدر/IR-Cut'] },
    { k: 'lens_holder_pitch', l: 'فاصله پیچ نصب هولدر', type: 'combo', choices: ['20mm'], hint: 'استاندارد رایج 20mm است' },
    { k: 'lens_fov', l: 'زاویه دید افقی (FOV)', hint: 'مثلاً 91.3° یا 30~100° برای وریفوکال' },
  ]},
  { title: 'مودم', fields: [
    { k: 'modem_model', l: 'مدل مودم' },
    { k: 'modem_type', l: 'نوع مودم' },
    { k: 'modem_size', l: 'سایز مودم' },
    { k: 'pin_count', l: 'تعداد پین' },
    { k: 'sim_card', l: 'سیم کارت' },
  ]},
  { title: 'متعلقات', fields: [
    { k: 'modem_model', l: 'مدل' },
    { k: 'modem_type', l: 'نوع' },
    { k: 'voltage', l: 'ولتاژ کاری', type: 'combo', choices: ['5V', '12V DC', '24V AC', '48V'] },
    { k: 'modem_size', l: 'سایز' },
  ]},
  { title: 'بدنه', fields: [
    { k: 'housing_material', l: 'جنس بدنه', choices: ['فلز', 'پلاستیک', 'فلز و پلاستیک'] },
    { k: 'housing_size', l: 'سایز بدنه' },
  ]},
  { title: 'اطلاعات فنی بیشتر', fields: [
    { k: 'board_tech_notes', l: 'اطلاعات فنی بیشتر', type: 'textarea' },
  ]},
  { title: 'سئو و جغرافیا (SEO/GEO)', fields: [
    { k: 'meta_title', l: 'عنوان متا (Meta Title)', hint: '۵۰–۶۰ کاراکتر — عنوان آبی لینک در نتایج گوگل؛ نام قطعه + مدل + برند' },
    { k: 'meta_description', l: 'توضیح متا (Meta Description)', type: 'textarea', hint: 'حداکثر ۱۶۰ کاراکتر — متن خاکستری زیر عنوان در گوگل؛ فایده اصلی + ویژگی کلیدی' },
    { k: 'keywords', l: 'کلمات کلیدی', hint: 'با ویرگول جدا کن — مثلاً: لنز ۵ مگاپیکسل، IR Cut، لنز YTOT، دوربین مداربسته' },
    { k: 'geo_tags', l: 'شهرهای هدف (GEO)', hint: 'شهر/مناطق هدف فروش با ویرگول — مثلاً: تهران، کرج، البرز' },
  ]},
  { title: 'وضعیت نمایش', fields: [
    { k: 'is_active', l: 'فعال (نمایش در فروشگاه)', type: 'checkbox' },
    { k: 'is_featured', l: 'محصول ویژه', type: 'checkbox' },
    { k: 'availability', l: 'وضعیت موجودی', hint: 'به‌زودی = محصول در راه است؛ توقف تولید = دیگر موجود نمی‌شود', choices: [
      { v: 'auto', l: 'خودکار (بر اساس موجودی انبار)' },
      { v: 'coming_soon', l: '🔜 به‌زودی' },
      { v: 'discontinued', l: '⛔ توقف تولید / ناموجود دائمی' },
    ]},
  ]},
]

// ─── گروه‌های مشخصات بر اساس نوع دسته ─────────────────────────
const SPEC_GROUPS_BY_TYPE = {
  board: ['برد', 'سنسور', 'اطلاعات فنی بیشتر'],
  lens: ['لنز'],
  modem: ['مودم'],
  accessory: ['متعلقات'],
  recorder: [],
  housing: ['بدنه'],
  // دوربین/دستگاه مونتاژشده (other) فقط ویژگی‌های سفارشی دسته را می‌گیرد —
  // گروه‌های پایه برد/لنز/مودم/بدنه برای محصول مونتاژشده گیج‌کننده است
  other: [],
}
const ALWAYS_GROUPS = ['اطلاعات اصلی', 'سئو و جغرافیا (SEO/GEO)', 'وضعیت نمایش']

// ─── مودال ویرایش محصول ───────────────────────────────────────
function ProductEditor({ productId, categories, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState(null)
  // محصولات سازگار — ids به‌همراه PATCH اصلی ذخیره می‌شود؛ names فقط برای نمایش چیپ‌هاست
  const [compatIds, setCompatIds] = useState(null)
  const [compatNames, setCompatNames] = useState({})

  const { data: productData, isLoading } = useQuery({
    queryKey: ['admin-product', productId],
    queryFn: () => api.get(`/catalog/products/admin/${productId}/`).then(r => r.data),
  })

  // داده (از کش یا فچ تازه) به state فرم منتقل می‌شود — قبلاً setForm داخل queryFn
  // بود و در باز شدن مجدد مودال (cache hit بدون اجرای مجدد queryFn) فرم خالی می‌ماند.
  // مقداردهی فقط یک‌بار (f ?? ...) انجام می‌شود تا refetch بعد از آپلود تصویر/دیتاشیت
  // ویرایش‌های ذخیره‌نشده کاربر را بازنویسی نکند.
  useEffect(() => {
    if (productData) {
      setForm(f => f ?? productData)
      setCompatIds(ids => ids ?? (productData.compatible_products || []).map(p => p.id))
      setCompatNames(m => Object.keys(m).length
        ? m
        : Object.fromEntries((productData.compatible_products || []).map(p => [p.id, p.name])))
    }
  }, [productData])

  const stockCommit = useRef(null) // ثبت موجودی‌های واردشده در StockSection هنگام «ذخیره تغییرات»

  const saveMut = useMutation({
    mutationFn: async (d) => {
      await api.patch(`/catalog/products/admin/${productId}/`, d).then(r => r.data)
      // اگر در بخش موجودی انبار مقداری تایپ شده، همان‌ها هم ثبت شوند
      return stockCommit.current ? stockCommit.current() : ''
    },
    onSuccess: (stockMsg) => {
      qc.invalidateQueries(['admin-products'])
      qc.invalidateQueries(['admin-product', productId])
      qc.invalidateQueries(['home-products'])
      toast.success(stockMsg ? `مشخصات ذخیره شد — ${stockMsg}` : 'مشخصات محصول ذخیره شد')
      onClose()
    },
    onError: (e) => {
      const d = e.response?.data
      const first = d && typeof d === 'object' ? Object.entries(d)[0] : null
      toast.error(first ? `${first[0]}: ${[].concat(first[1])[0]}` : (e.message || 'خطا در ذخیره'))
    },
  })

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/catalog/products/admin/${productId}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-products'])
      qc.invalidateQueries(['home-products'])
      toast.success('محصول حذف شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف محصول'),
  })

  const [confirmDelete, setConfirmDelete] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const setSpec = (k, v) => setForm(f => ({ ...f, dynamic_specs: { ...(f.dynamic_specs || {}), [k]: v } }))

  // payload ذخیره — فیلدهای read-only (تصاویر، لیست نمایشی سازگار، آدرس دیتاشیت)
  // ارسال نمی‌شوند؛ compatible_with فقط به‌صورت لیست id می‌رود
  const buildPayload = () => {
    const { images, compatible_products, datasheet_pdf, has_datasheet, ...payload } = form
    return { ...payload, compatible_with: compatIds || [] }
  }

  // فیلتر گروه‌های مشخصات بر اساس نوع دسته محصول (واکنش‌گرا به تغییر دسته)
  const currentCat = categories.find(c => c.id === form?.category)
  // دو باکس جدا: دسته اصلی + زیردسته‌های همان دسته
  const rootOptions = categories.filter(c => !c.parent)
  const selectedRootId = currentCat ? (currentCat.parent || currentCat.id) : ''
  const childOptions = categories.filter(c => c.parent === selectedRootId)

  // فیلدهای پایه/مخفی/بازنویسی/برند از دسته اصلی خوانده می‌شود؛
  // ویژگی‌های سفارشی = ویژگی‌های دسته اصلی + ویژگی‌های اختصاصی خود زیردسته (ادغام)
  const parentCat = currentCat?.parent ? categories.find(c => c.id === currentCat.parent) : null
  const effectiveCat = parentCat || currentCat
  // گزینه‌های دراپ‌داون برند — برندهای تعریف‌شده/در حال استفاده همین دسته (مدیریت در صفحه ویژگی‌های دسته‌ها)
  const brandOptions = effectiveCat?.brands || []

  // اعمال بازنویسی لیبل/گزینه‌های فیلدهای پایه (تعریف‌شده در مدیریت دسته‌بندی)
  const applyOverride = (f) => {
    const ov = (effectiveCat?.field_overrides || {})[f.k]
    if (!ov) return f
    return {
      ...f,
      l: ov.label || f.l,
      choices: ov.choices ? ov.choices.split(/[,،]/).map(x => x.trim()).filter(Boolean) : f.choices,
    }
  }

  // فیلدهای شرطی بر اساس «سیستم برد»: ویژگی‌های زیردسته AHD فقط وقتی سیستم AHD
  // انتخاب شده نمایش داده می‌شوند (و برعکس برای IP). هر فیلد با اسلاگ دسته مبدأ
  // علامت می‌خورد تا منشأش مشخص بماند. اگر محصول مستقیماً در ریشه برد باشد،
  // فیلدهای زیردسته مطابق با سیستم انتخاب‌شده هم به فرم اضافه می‌شوند.
  const BOARD_SYS_BY_SLUG = { 'ahd-camera-board': 'AHD', 'ip-camera-board': 'IP' }
  // فیلدهای مشترک دسته برد که فقط برای IP معنا دارند — در حالت AHD مخفی می‌شوند
  const AHD_HIDDEN_SHARED = new Set(['مکالمه-دوطرفه', 'خروجی-آلارم', 'امپلی-فایر-داخلی'])
  const boardSys = form?.board_system || ''
  let specFieldList = (currentCat?.parent
    ? [...(parentCat?.spec_fields || []).map(f => ({ ...f, _catSlug: parentCat.slug })),
       ...(currentCat?.spec_fields || []).map(f => ({ ...f, _catSlug: currentCat.slug }))]
    : (currentCat?.spec_fields || []).map(f => ({ ...f, _catSlug: currentCat?.slug })))
  if (boardSys && currentCat && !currentCat.parent && currentCat.category_type === 'board') {
    const sysCat = categories.find(c => BOARD_SYS_BY_SLUG[c.slug] === boardSys)
    if (sysCat) specFieldList = [...specFieldList, ...(sysCat.spec_fields || []).map(f => ({ ...f, _catSlug: sysCat.slug }))]
  }
  const activeSpecFields = specFieldList
    .filter(f => f.is_active)
    // کلید تکراری (هم‌نام روی والد و فرزند) فقط یک‌بار — تعریف والد مقدم است (مثل get_specs سایت)
    .filter((f, i, arr) => arr.findIndex(x => x.key === f.key) === i)
    // فیلد مخصوص یک سیستم برد فقط وقتی همان سیستم انتخاب شده باشد می‌آید؛
    // تا وقتی سیستم انتخاب نشده، هر دو گروه دیده می‌شوند
    .filter(f => { const sys = BOARD_SYS_BY_SLUG[f._catSlug]; return !sys || !boardSys || sys === boardSys })
    // برد AHD رم و صدای دوطرفه/آلارم ندارد — این فیلدهای مشترک در حالت AHD مخفی می‌شوند
    .filter(f => !(boardSys === 'AHD' && AHD_HIDDEN_SHARED.has(f.key)))
    // چک‌باکس قدیمی «پشتیبانی از کارت حافظه» از فرم حذف شد — دراپ‌داون «حداکثر ظرفیت
    // کارت حافظه» (با گزینه «ندارد») جایگزینش است
    .filter(f => f.key !== 'پشتیبانی-از-کارت-حافظه')
  const specTitles = currentCat?.category_type ? SPEC_GROUPS_BY_TYPE[currentCat.category_type] : null
  const hiddenKeys = new Set(effectiveCat?.hidden_fields || [])
  const visibleGroups = FIELD_GROUPS
    .filter(g => ALWAYS_GROUPS.includes(g.title) || !specTitles || specTitles.includes(g.title))
    .map(g => hiddenKeys.size ? { ...g, fields: g.fields.filter(f => !hiddenKeys.has(f.k)) } : g)
    .filter(g => g.fields.length > 0)

  // ویژگی‌های سفارشی دسته بالای «اطلاعات فنی بیشتر» درج می‌شود؛ اگر آن گروه برای
  // این نوع دسته فعال نباشد، قبل از گروه سئو قرار می‌گیرد
  const specInsertBefore = visibleGroups.some(g => g.title === 'اطلاعات فنی بیشتر')
    ? 'اطلاعات فنی بیشتر'
    : 'سئو و جغرافیا (SEO/GEO)'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-bold text-white text-lg">ویرایش محصول</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>
        {form?.slug && (
          <div className="text-[11px] text-gray-steel mb-3">
            آدرس محصول:{' '}
            <a href={`/products/${form.slug}`} target="_blank" rel="noreferrer"
              className="font-mono text-brand hover:underline" dir="ltr">/products/{form.slug}/</a>
          </div>
        )}
        {specTitles && (
          <div className="text-[11px] text-gray-steel mb-3">
            فقط مشخصات مرتبط با دسته «{currentCat.name}» نمایش داده می‌شود — با تغییر دسته یا «سیستم برد» (IP/AHD)، بخش‌ها به‌روز می‌شوند.
          </div>
        )}

        {isLoading || !form ? <PageLoader /> : (
          <>
            {visibleGroups.map(g => (
              <Fragment key={g.title}>
              {/* ویژگی‌های سفارشی دسته — تعریف‌شده در «ویژگی‌های دسته‌ها»؛ مقادیر در dynamic_specs ذخیره می‌شود */}
              {g.title === specInsertBefore && activeSpecFields.length > 0 && (
                <div className="mb-5">
                  <div className="text-xs font-bold text-gold mb-2 flex items-center gap-2">
                    <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
                    ویژگی‌های «{effectiveCat.name}»
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {activeSpecFields.map(f => (
                      <div key={f.key}>
                        {f.field_type === 'checkbox' ? (
                          <label className="flex items-center gap-2 cursor-pointer mt-5">
                            <input type="checkbox" checked={!!(form.dynamic_specs || {})[f.key]}
                              onChange={e => setSpec(f.key, e.target.checked)}
                              className="w-4 h-4 accent-[#FBC02D]" />
                            <span className="text-xs text-gray-steel">{f.label}</span>
                          </label>
                        ) : f.field_type === 'select' ? (
                          <>
                            <label className="label text-xs mb-1 block">{f.label}</label>
                            <select value={(form.dynamic_specs || {})[f.key] || ''}
                              onChange={e => setSpec(f.key, e.target.value)}
                              className="input-dark text-xs w-full">
                              <option value="">—</option>
                              {(f.choices || '').split(/[,،]/).map(x => x.trim()).filter(Boolean)
                                .map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                          </>
                        ) : (
                          <>
                            <label className="label text-xs mb-1 block">{f.label}</label>
                            <input value={(form.dynamic_specs || {})[f.key] || ''}
                              onChange={e => setSpec(f.key, e.target.value)}
                              className="input-dark text-xs w-full" />
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="mb-5">
                <div className="text-xs font-bold text-gold mb-2 flex items-center gap-2">
                  <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
                  {g.title}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {g.fields.map(f0 => {
                    const f = applyOverride(f0)
                    return (
                    <div key={f.k} className={f.type === 'textarea' ? 'col-span-2 md:col-span-3' : f.type === 'category' ? 'col-span-2' : ''}>
                      {f.type === 'checkbox' ? (
                        <label className="flex items-center gap-2 cursor-pointer mt-5">
                          <input type="checkbox" checked={!!form[f.k]} onChange={e => set(f.k, e.target.checked)}
                            className="w-4 h-4 accent-[#FBC02D]" />
                          <span className="text-xs text-gray-steel">{f.l}</span>
                        </label>
                      ) : f.type === 'textarea' ? (
                        <>
                          <label className="label text-xs mb-1 block">{f.l}</label>
                          <textarea value={form[f.k] || ''} onChange={e => set(f.k, e.target.value)}
                            rows={3} className="input-dark text-xs w-full" />
                        </>
                      ) : f.type === 'category' ? (
                        <div className="col-span-2 grid grid-cols-2 gap-3">
                          <div>
                            <label className="label text-xs mb-1 block">دسته اصلی</label>
                            <select value={selectedRootId} onChange={e => set(f.k, e.target.value ? Number(e.target.value) : null)}
                              className="input-dark text-xs w-full">
                              <option value="">انتخاب کنید...</option>
                              {rootOptions.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="label text-xs mb-1 block">زیردسته</label>
                            <select
                              value={currentCat?.parent ? currentCat.id : ''}
                              onChange={e => set(f.k, e.target.value ? Number(e.target.value) : Number(selectedRootId))}
                              disabled={!selectedRootId || childOptions.length === 0}
                              className="input-dark text-xs w-full disabled:opacity-40">
                              <option value="">{childOptions.length ? 'بدون زیردسته (همان دسته اصلی)' : 'زیردسته ندارد'}</option>
                              {childOptions.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                          </div>
                        </div>
                      ) : f.type === 'brand' ? (
                        <>
                          <label className="label text-xs mb-1 block">{f.l}</label>
                          <select value={form[f.k] || ''} onChange={e => set(f.k, e.target.value)}
                            className="input-dark text-xs w-full">
                            <option value="">—</option>
                            {/* اگر برند فعلی محصول در لیست نیست، نمایش داده شود تا گم نشود */}
                            {[...new Set([...(form[f.k] ? [form[f.k]] : []), ...brandOptions])]
                              .map(b => <option key={b} value={b}>{b}</option>)}
                          </select>
                        </>
                      ) : f.type === 'combo' ? (
                        <>
                          <label className="label text-xs mb-1 block">{f.l}</label>
                          <input list={`dl-${f.k}`} value={form[f.k] || ''} onChange={e => set(f.k, e.target.value)}
                            dir={f.dir} className="input-dark text-xs w-full" />
                          <datalist id={`dl-${f.k}`}>
                            {(f.choices || []).map(c => <option key={c} value={c} />)}
                          </datalist>
                        </>
                      ) : f.choices ? (
                        <>
                          <label className="label text-xs mb-1 block">{f.l}</label>
                          <select value={form[f.k] || ''} onChange={e => set(f.k, e.target.value)}
                            className="input-dark text-xs w-full">
                            {/* گزینه‌های آبجکتی ({v,l}) مقدار ثابت دارند و گزینه خالی نمی‌گیرند */}
                            {typeof f.choices[0] !== 'object' && <option value="">—</option>}
                            {f.choices.map(c => typeof c === 'object'
                              ? <option key={c.v} value={c.v}>{c.l}</option>
                              : <option key={c} value={c}>{c}</option>)}
                          </select>
                        </>
                      ) : (
                        <>
                          <label className="label text-xs mb-1 block">{f.l}</label>
                          <input value={form[f.k] || ''} onChange={e => set(f.k, e.target.value)}
                            dir={f.dir} className="input-dark text-xs w-full" />
                        </>
                      )}
                      {f.hint && <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">{f.hint}</div>}
                      {f.k === 'meta_title' && <CharCount value={form[f.k]} min={50} max={60} />}
                      {f.k === 'meta_description' && <CharCount value={form[f.k]} min={70} max={160} />}
                    </div>
                    )
                  })}
                </div>
                {g.title.startsWith('سئو') && (
                  <div className="text-[10px] text-[var(--color-text-muted)] mt-2 leading-relaxed border-t border-white/5 pt-2">
                    💡 فیلدهای خالی هنگام ذخیره به‌صورت خودکار از نام و مشخصات محصول ساخته می‌شوند.
                    {' '}آدرس محصول: <span className="font-mono text-brand" dir="ltr">/products/{form.slug}</span>
                  </div>
                )}
              </div>
              </Fragment>
            ))}

            <ImagesSection productId={productId} images={form.images || []}
              onChange={imgs => set('images', imgs)} />

            <DatasheetSection productId={productId} pdfUrl={form.datasheet_pdf}
              onChange={v => set('datasheet_pdf', v)} />

            <CompatibleSection productId={productId}
              ids={compatIds || []} setIds={setCompatIds}
              names={compatNames} setNames={setCompatNames} />

            <StockSection productId={productId} variants={form.variants || []}
              registerCommit={fn => { stockCommit.current = fn }} />

            <div className="flex gap-2 pt-2 border-t border-[var(--color-border)]">
              <button onClick={() => saveMut.mutate(buildPayload())} disabled={!form.name || saveMut.isPending}
                className="btn-primary px-6 py-2.5 disabled:opacity-50">
                {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
              </button>
              <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
              {confirmDelete ? (
                <div className="mr-auto flex items-center gap-2">
                  <span className="text-[11px] text-red-400">محصول برای همیشه حذف شود؟</span>
                  <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                    className="text-xs px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 disabled:opacity-50">
                    {deleteMut.isPending ? '...' : 'بله، حذف کن'}
                  </button>
                  <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-steel hover:text-white">خیر</button>
                </div>
              ) : (
                <button onClick={() => setConfirmDelete(true)}
                  className="mr-auto text-xs px-4 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors">
                  🗑 حذف محصول
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ─── هدر مشترک بخش‌ها (همان سبک گروه‌های مشخصات) ─────────────
const SectionTitle = ({ children }) => (
  <div className="text-xs font-bold text-gold mb-2 flex items-center gap-2">
    <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
    {children}
  </div>
)

// ─── بخش تصاویر محصول در ویرایشگر ────────────────────────────
function ImagesSection({ productId, images, onChange }) {
  const qc = useQueryClient()
  const [pending, setPending] = useState(false)
  const [confirmId, setConfirmId] = useState(null)

  const refresh = () => {
    qc.invalidateQueries(['admin-product', productId])
    qc.invalidateQueries(['admin-products'])
  }

  const upload = async (files) => {
    if (!files?.length) return
    setPending(true)
    try {
      let acc = images // تجمیع محلی تا آپلودهای پشت‌سرهم (چند فایل) همدیگر را بازنویسی نکنند
      for (const file of Array.from(files)) {
        const fd = new FormData()
        fd.append('image', file)
        const r = await api.post(`/catalog/products/admin/${productId}/images/`, fd)
        acc = [...acc, r.data]
        onChange(acc)
      }
      toast.success('تصویر آپلود شد')
      refresh()
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در آپلود تصویر')
    } finally {
      setPending(false)
    }
  }

  const setPrimary = async (img) => {
    if (img.is_primary) return
    try {
      await api.post(`/catalog/products/admin/images/${img.id}/primary/`)
      onChange(images.map(i => ({ ...i, is_primary: i.id === img.id })))
      refresh()
    } catch {
      toast.error('خطا در تنظیم تصویر اصلی')
    }
  }

  const saveAlt = async (img, value) => {
    const alt = (value || '').trim()
    if (alt === (img.alt_text || '')) return
    try {
      await api.patch(`/catalog/products/admin/images/${img.id}/`, { alt_text: alt })
      onChange(images.map(i => (i.id === img.id ? { ...i, alt_text: alt } : i)))
      toast.success('متن جایگزین ذخیره شد')
    } catch {
      toast.error('خطا در ذخیره متن جایگزین')
    }
  }

  const remove = async (img) => {
    try {
      await api.delete(`/catalog/products/admin/images/${img.id}/`)
      onChange(images.filter(i => i.id !== img.id))
      toast.success('تصویر حذف شد')
      refresh()
    } catch {
      toast.error('خطا در حذف تصویر')
    } finally {
      setConfirmId(null)
    }
  }

  return (
    <div className="mb-5">
      <SectionTitle>
        تصاویر محصول
        <label className={`mr-auto btn-secondary text-xs px-3 py-1.5 cursor-pointer inline-flex items-center gap-1.5 ${pending ? 'opacity-50 pointer-events-none' : ''}`}>
          <Upload size={13} />
          {pending ? 'در حال آپلود...' : 'آپلود تصویر'}
          <input type="file" accept="image/*" multiple className="hidden"
            onChange={e => { upload(e.target.files); e.target.value = '' }} />
        </label>
      </SectionTitle>
      <div className="text-[10px] text-[var(--color-text-muted)] mb-2">
        ابعاد پیشنهادی: ۱۰۰۰×۱۰۰۰ پیکسل (مربع) — فرمت JPG یا WebP — حجم تا ۳۰۰ کیلوبایت.
      </div>
      {images.length === 0 ? (
        <div className="text-[11px] text-[var(--color-text-muted)]">هنوز تصویری ثبت نشده است.</div>
      ) : (
        <div className="grid grid-cols-3 md:grid-cols-4 gap-3">
          {images.map(img => (
            <div key={img.id} className="relative rounded-xl border border-[var(--color-border)] overflow-hidden group">
              <img src={mediaUrl(img.image)} alt={img.alt_text || ''} className="w-full h-24 object-cover bg-black/30" />
              {img.is_primary && (
                <span className="absolute top-1.5 right-1.5 badge-gold badge text-[10px] inline-flex items-center gap-1">
                  <Star size={10} /> اصلی
                </span>
              )}
              <div className="flex items-center justify-between px-2 py-1.5">
                <label title="تنظیم به‌عنوان تصویر اصلی"
                  className={`flex items-center gap-1 text-[10px] select-none transition-colors ${img.is_primary ? 'text-gold' : 'text-gray-steel hover:text-gold cursor-pointer'}`}>
                  <input type="checkbox" checked={img.is_primary} disabled={img.is_primary}
                    onChange={() => setPrimary(img)}
                    className="w-3.5 h-3.5 accent-yellow-500 cursor-pointer" />
                  <Star size={12} fill={img.is_primary ? 'currentColor' : 'none'} />
                  عکس اصلی
                </label>
                {confirmId === img.id ? (
                  <span className="flex items-center gap-1.5 text-[10px]">
                    <button onClick={() => remove(img)} className="text-red-400 hover:text-red-300">حذف؟</button>
                    <button onClick={() => setConfirmId(null)} className="text-gray-steel hover:text-white">خیر</button>
                  </span>
                ) : (
                  <button onClick={() => setConfirmId(img.id)} title="حذف تصویر"
                    className="text-gray-steel hover:text-red-400 transition-colors">
                    <X size={15} />
                  </button>
                )}
              </div>
              {/* متن جایگزین (alt) — مهم برای سئو؛ با خروج از فیلد ذخیره می‌شود */}
              <input
                type="text"
                defaultValue={img.alt_text || ''}
                placeholder="متن جایگزین (alt)"
                title="متن جایگزین تصویر برای سئو — با Enter یا خروج از فیلد ذخیره می‌شود"
                onBlur={e => saveAlt(img, e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') e.target.blur() }}
                className="w-full text-[10px] px-2 py-1.5 bg-transparent border-t border-[var(--color-border)] text-gray-steel focus:text-white focus:outline-none placeholder:text-[var(--color-text-muted)]"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── بخش دیتاشیت (PDF) در ویرایشگر ───────────────────────────
function DatasheetSection({ productId, pdfUrl, onChange }) {
  const qc = useQueryClient()
  const [pending, setPending] = useState(false)

  const refresh = () => {
    qc.invalidateQueries(['admin-product', productId])
    qc.invalidateQueries(['admin-products'])
  }

  const upload = async (file) => {
    if (!file) return
    const fd = new FormData()
    fd.append('datasheet_pdf', file)
    setPending(true)
    try {
      const r = await api.patch(`/catalog/products/admin/${productId}/`, fd)
      onChange(r.data.datasheet_pdf)
      toast.success('دیتاشیت آپلود شد')
      refresh()
    } catch (e) {
      toast.error(e.response?.data?.datasheet_pdf?.[0] || 'خطا در آپلود دیتاشیت')
    } finally {
      setPending(false)
    }
  }

  // حذف دیتاشیت با PATCH جی‌سونی null انجام می‌شود (multipart رشته خالی قبول نمی‌کند)
  const clear = async () => {
    setPending(true)
    try {
      await api.patch(`/catalog/products/admin/${productId}/`, { datasheet_pdf: null })
      onChange(null)
      toast.success('دیتاشیت حذف شد')
      refresh()
    } catch {
      toast.error('خطا در حذف دیتاشیت')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mb-5">
      <SectionTitle>دیتاشیت (PDF)</SectionTitle>
      {pdfUrl ? (
        <div className="flex items-center gap-3 rounded-xl border border-[var(--color-border)] px-3 py-2.5">
          <FileText size={18} className="text-gold shrink-0" />
          <a href={mediaUrl(pdfUrl)} target="_blank" rel="noreferrer"
            className="text-xs text-gold hover:underline">مشاهده دیتاشیت فعلی</a>
          <button onClick={clear} disabled={pending}
            className="mr-auto text-xs px-3 py-1.5 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors disabled:opacity-50">
            {pending ? '...' : 'حذف'}
          </button>
        </div>
      ) : (
        <label className={`btn-secondary text-xs px-3 py-2 cursor-pointer inline-flex items-center gap-1.5 ${pending ? 'opacity-50 pointer-events-none' : ''}`}>
          <Upload size={13} />
          {pending ? 'در حال آپلود...' : 'آپلود فایل PDF'}
          <input type="file" accept=".pdf,application/pdf" className="hidden"
            onChange={e => { upload(e.target.files?.[0]); e.target.value = '' }} />
        </label>
      )}
    </div>
  )
}

// ─── بخش محصولات سازگار در ویرایشگر ──────────────────────────
function CompatibleSection({ productId, ids, setIds, names, setNames }) {
  const [q, setQ] = useState('')
  const [dq, setDq] = useState('') // مقدار debounce‌شده (~۳۰۰ms)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDq(q), 300)
    return () => clearTimeout(t)
  }, [q])

  // با فوکوس روی اینپوت، لیست همه محصولات باز می‌شود؛ با تایپ، همان لیست فیلتر می‌شود
  const { data: matches = [], isFetching } = useQuery({
    queryKey: ['compat-search', dq],
    queryFn: () => api.get('/catalog/products/', { params: { search: dq, page_size: 50 } })
      .then(r => r.data.results || []),
    enabled: open,
  })

  const options = matches.filter(p => p.id !== productId && !ids.includes(p.id))

  const add = (p) => {
    setIds([...ids, p.id])
    setNames({ ...names, [p.id]: p.name })
    setQ('')
    setDq('')
  }
  const remove = (id) => setIds(ids.filter(x => x !== id))

  return (
    <div className="mb-5">
      <SectionTitle>محصولات سازگار</SectionTitle>
      {ids.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {ids.map(id => (
            <span key={id} className="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full border border-[var(--color-border)] bg-black/20">
              {names[id] || `#${id}`}
              <button onClick={() => remove(id)} className="text-gray-steel hover:text-red-400 transition-colors" title="حذف">
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="relative">
        <Search size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
        <input value={q} onChange={e => setQ(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          placeholder="کلیک کنید و از لیست انتخاب کنید یا جستجو کنید..."
          className="input-dark text-xs w-full" style={{ paddingRight: '2rem' }} />
        {open && (options.length > 0 || isFetching) && (
          <div className="absolute z-10 mt-1 w-full card p-1.5 max-h-48 overflow-y-auto">
            {isFetching && options.length === 0 && (
              <div className="text-[11px] text-gray-steel px-2 py-1.5">در حال بارگذاری...</div>
            )}
            {options.map(p => (
              <button key={p.id} onClick={() => add(p)}
                className="w-full text-right text-xs px-2.5 py-2 rounded-lg hover:bg-[var(--color-brand-softer)] transition-colors">
                {p.name}
              </button>
            ))}
            {!isFetching && options.length === 0 && (
              <div className="text-[11px] text-gray-steel px-2 py-1.5">موردی یافت نشد</div>
            )}
          </div>
        )}
      </div>
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">
        تغییرات این بخش با دکمه «ذخیره تغییرات» همراه مشخصات محصول ذخیره می‌شود.
      </div>
    </div>
  )
}

// ─── بخش ثبت موجودی اولیه در ویرایشگر محصول ───────────────────
function StockSection({ productId, variants, registerCommit }) {
  const qc = useQueryClient()
  const [qty, setQty] = useState({})       // variantId → مقدار ورودی
  const [costs, setCosts] = useState({})   // variantId → {purchase, shipping, clearance}
  const [pending, setPending] = useState(null)
  const [warehouseId, setWarehouseId] = useState('')

  // نرخ یوان روز برای محاسبه زنده بهای تمام‌شده
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  const rate = Number(rateData?.rate_cny_to_irt || 0)

  // انبارها برای انتخاب مقصد موجودی اولیه
  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => api.get('/inventory/warehouses/').then(r => r.data),
  })
  const warehouses = Array.isArray(warehousesData)
    ? warehousesData
    : (warehousesData?.results || warehousesData?.data || [])

  if (!variants.length) return null

  const setCost = (id, k, val) => setCosts(s => ({ ...s, [id]: { ...s[id], [k]: val } }))
  const costVals = (v) => ({
    purchase:  costs[v.id]?.purchase  ?? String(v.purchase_price_cny ?? 0),
    shipping:  costs[v.id]?.shipping  ?? String(v.shipping_cost_cny ?? 0),
    clearance: costs[v.id]?.clearance ?? '',
  })
  // بهای تمام‌شده واحد (ریال) = (خرید + حمل) × نرخ یوان + ترخیص
  const unitCost = (v) => {
    const c = costVals(v)
    return Math.round((Number(c.purchase || 0) + Number(c.shipping || 0)) * rate + Number(c.clearance || 0))
  }

  const submit = async (v) => {
    const n = Number(qty[v.id] || 0)
    if (!n || n <= 0) { toast.error('مقدار موجودی را وارد کنید'); return }
    if (!warehouseId) { toast.error('انبار مقصد موجودی را انتخاب کنید'); return }
    const c = costVals(v)
    setPending(v.id)
    try {
      const r = await api.post(`/catalog/products/admin/${productId}/opening-stock/`, {
        variant_id: v.id,
        quantity: n,
        warehouse_id: warehouseId,
        purchase_price_cny: Number(c.purchase) || 0,
        shipping_cost_cny: Number(c.shipping) || 0,
        clearance_cost_irr: Number(c.clearance) || 0,
      })
      toast.success(
        `موجودی ثبت شد — بهای واحد: ${Number(r.data.unit_cost_irr).toLocaleString('fa-IR')} ریال | سرمایه: ${Number(r.data.total_cost_irr).toLocaleString('fa-IR')} ریال`
      )
      setQty(q => ({ ...q, [v.id]: '' }))
      qc.invalidateQueries(['admin-product', productId])
      qc.invalidateQueries(['admin-products'])
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ثبت موجودی')
    } finally {
      setPending(null)
    }
  }

  // ثبت همه موجودی‌های تایپ‌شده هنگام کلیک «ذخیره تغییرات» اصلی فرم —
  // چون کاربر انتظار دارد دکمه اصلی ذخیره، موجودی را هم ثبت کند
  const commitAll = async () => {
    const entries = variants.filter(v => Number(qty[v.id] || 0) > 0)
    if (!entries.length) return ''
    if (!warehouseId) throw new Error('انبار مقصد موجودی را انتخاب کنید')
    let done = 0
    for (const v of entries) {
      const c = costVals(v)
      await api.post(`/catalog/products/admin/${productId}/opening-stock/`, {
        variant_id: v.id,
        quantity: Number(qty[v.id]),
        warehouse_id: warehouseId,
        purchase_price_cny: Number(c.purchase) || 0,
        shipping_cost_cny: Number(c.shipping) || 0,
        clearance_cost_irr: Number(c.clearance) || 0,
      })
      done += 1
    }
    setQty({})
    return `موجودی ${done.toLocaleString('fa-IR')} واریانت ثبت شد`
  }

  useEffect(() => {
    if (registerCommit) registerCommit(commitAll)
  })

  const inp = 'input-dark text-xs w-24 text-center'

  return (
    <div className="mb-5">
      <div className="text-xs font-bold text-gold mb-2 flex items-center gap-2">
        <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
        موجودی انبار
        <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)}
          className="input-dark text-xs mr-auto px-2 py-1.5">
          <option value="">انتخاب انبار مقصد *</option>
          {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </div>
      <div className="space-y-2">
        {variants.map(v => (
          <div key={v.id} className="rounded-xl border border-[var(--color-border)] px-3 py-2 space-y-2">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-mono text-[11px] text-gray-steel" dir="ltr">{v.sku}</span>
              {v.name_suffix && <span className="text-[11px] text-gray-steel">{v.name_suffix}</span>}
              <span className={`text-[11px] ${v.available_stock > 0 ? 'text-green-500' : 'text-red-400'}`}>
                موجودی فعلی: {Number(v.available_stock || 0).toLocaleString('fa-IR')}
              </span>
              <div className="flex items-center gap-2 mr-auto">
                <AmountInput value={qty[v.id] || ''} onChange={e => setQty(q => ({ ...q, [v.id]: e.target.value }))}
                  placeholder="موجودی اولیه" className="input-dark text-xs w-24" />
                <button onClick={() => submit(v)} disabled={pending === v.id}
                  className="btn-secondary text-xs px-3 py-1.5 disabled:opacity-50">
                  {pending === v.id ? '...' : 'ثبت'}
                </button>
              </div>
            </div>
            {/* هزینه‌های تمام‌شده — برای محاسبه سرمایه در گردش (حسابداری) */}
            <div className="flex items-center gap-2 flex-wrap text-[10px] text-gray-steel">
              <span>قیمت خرید (یوان):</span>
              <AmountInput value={costVals(v).purchase} onChange={e => setCost(v.id, 'purchase', e.target.value)} className={inp} />
              <span>حمل (یوان):</span>
              <AmountInput value={costVals(v).shipping} onChange={e => setCost(v.id, 'shipping', e.target.value)} className={inp} />
              <span>ترخیص (ریال):</span>
              <AmountInput value={costVals(v).clearance} onChange={e => setCost(v.id, 'clearance', e.target.value)} className={inp} placeholder="۰" />
              <span className="mr-auto text-[11px]">
                بهای واحد: <span className="font-bold text-gold">{unitCost(v).toLocaleString('fa-IR')} ریال</span>
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">
        مقدار واردشده به موجودی فعلی اضافه می‌شود و با بهای تمام‌شده واحد ((خرید + حمل) × نرخ یوان + ترخیص) در کاردکسِ انبار انتخاب‌شده به‌عنوان «موجودی اول دوره» ثبت می‌گردد.
      </div>
    </div>
  )
}

// ─── مودال ساخت محصول جدید — بعد از ساخت، ویرایشگر کامل باز می‌شود ──
function NewProductModal({ categories, onCreated, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ name: '', rootId: '', childId: '', model_number: '' })

  const rootOptions = categories.filter(c => !c.parent)
  const childOptions = categories.filter(c => c.parent === Number(form.rootId))

  const createMut = useMutation({
    mutationFn: (d) => api.post('/catalog/products/admin/', d).then(r => r.data),
    onSuccess: (p) => {
      qc.invalidateQueries(['admin-products'])
      toast.success('محصول ساخته شد — حالا مشخصات را کامل کنید')
      onCreated(p.id)
    },
    onError: (e) => {
      const d = e.response?.data
      const first = d && typeof d === 'object' ? Object.entries(d)[0] : null
      toast.error(first ? `${first[0]}: ${[].concat(first[1])[0]}` : 'خطا در ساخت محصول')
    },
  })

  const submit = () => {
    const category = Number(form.childId || form.rootId)
    if (!form.name.trim() || !category) return
    createMut.mutate({ name: form.name.trim(), category, model_number: form.model_number.trim() })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">محصول جدید</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="label text-xs mb-1 block">نام محصول *</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="input-dark text-sm w-full" placeholder="مثلاً: برد دوربین IP پنج مگاپیکسل H2P" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label text-xs mb-1 block">دسته اصلی *</label>
              <select value={form.rootId} onChange={e => setForm(f => ({ ...f, rootId: e.target.value, childId: '' }))}
                className="input-dark text-xs w-full">
                <option value="">انتخاب کنید...</option>
                {rootOptions.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">زیردسته</label>
              <select value={form.childId} onChange={e => setForm(f => ({ ...f, childId: e.target.value }))}
                disabled={!form.rootId || childOptions.length === 0}
                className="input-dark text-xs w-full disabled:opacity-40">
                <option value="">{childOptions.length ? 'بدون زیردسته' : 'زیردسته ندارد'}</option>
                {childOptions.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label text-xs mb-1 block">شماره مدل</label>
            <input value={form.model_number} onChange={e => setForm(f => ({ ...f, model_number: e.target.value }))}
              className="input-dark text-sm w-full" dir="ltr" placeholder="اختیاری" />
          </div>
          <div className="text-[10px] text-[var(--color-text-muted)] leading-relaxed">
            یک واریانت پیش‌فرض با SKU خودکار ساخته می‌شود — قیمت، موجودی، تصویر و بقیه مشخصات را در مرحله بعد (ویرایشگر) کامل کنید.
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={submit}
            disabled={!form.name.trim() || !(form.childId || form.rootId) || createMut.isPending}
            className="btn-primary flex-1 py-2.5 text-sm disabled:opacity-50">
            {createMut.isPending ? 'در حال ساخت...' : 'ساخت و ادامه'}
          </button>
          <button onClick={onClose} className="btn-secondary px-5 py-2.5 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── صفحه مدیریت محصولات ──────────────────────────────────────
export default function AdminProductsPage() {
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState(null) // id محصول در حال ویرایش
  const [creating, setCreating] = useState(false)
  const [catFilter, setCatFilter] = useState('')        // فیلتر دسته اصلی
  const [subCatFilter, setSubCatFilter] = useState('')  // فیلتر زیردسته (وابسته به دسته اصلی)
  const [stockFilter, setStockFilter] = useState('')    // '' | 'in' | 'out' | 'discontinued'
  const [onlyFeatured, setOnlyFeatured] = useState(false)
  const [showInactive, setShowInactive] = useState(false) // محصولات غیرفعال (توقف تولید)

  const { data: categories = [] } = useQuery({
    queryKey: ['admin-categories-full'],
    queryFn: () => api.get('/catalog/categories/admin/').then(r => r.data.results || r.data || []),
  })

  const { data: products = [], isLoading } = useQuery({
    queryKey: ['admin-products', q],
    // include_inactive فقط برای پرسنل اثر دارد — غیرفعال‌ها هم بیایند تا با چک‌باکس قابل نمایش باشند
    queryFn: () => q.trim().length >= 2
      ? api.get('/catalog/products/search/', { params: { q: q.trim(), include_inactive: 1 } }).then(r => r.data.results || [])
      // لیست کامل محصولات — API صفحه‌بندی می‌کند، پس همه صفحه‌ها دنبال می‌شود
      : api.get('/catalog/products/', { params: { include_inactive: 1 } }).then(async r => {
          let all = r.data.results || []
          let next = r.data.next
          while (next) {
            // next آدرس مطلق است؛ به مسیر نسبی تبدیل می‌شود تا از همان baseURL/pروکسی برود
            const res = await api.get(next.replace(/^https?:\/\/[^/]+\/api/, ''))
            all = all.concat(res.data.results || [])
            next = res.data.next
          }
          return all
        }),
  })

  // فیلتر نوع کالا + وضعیت فعال — غیرفعال‌ها (توقف تولید) پیش‌فرض پنهان‌اند
  // مگر با چک‌باکس نمایش داده شوند یا در نتیجه جستجو باشند؛ فعال‌ها هم اول می‌آیند
  const catById = Object.fromEntries(categories.map(c => [c.id, c]))
  const rootCategories = categories.filter(c => !c.parent)
  const searching = q.trim().length >= 2
  const matchCat = (p) => {
    if (subCatFilter) return p.category_id === Number(subCatFilter)
    if (!catFilter) return true
    const c = catById[p.category_id]
    return c && (c.id === Number(catFilter) || c.parent === Number(catFilter))
  }
  const subCatOptions = catFilter ? categories.filter(c => c.parent === Number(catFilter)) : []
  const visibleProducts = products
    .filter(p => (searching || showInactive || p.is_active) && matchCat(p))
    .filter(p => {
      if (stockFilter === 'discontinued') return p.availability === 'discontinued'
      if (stockFilter === 'in') return (p.total_stock ?? p.available_stock) > 0
      if (stockFilter === 'out') return (p.total_stock ?? p.available_stock) <= 0
      return true
    })
    .filter(p => !onlyFeatured || p.is_featured)
    .sort((a, b) => (b.is_active ? 1 : 0) - (a.is_active ? 1 : 0))

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h1 className="font-display font-bold text-2xl text-white">مدیریت محصولات</h1>
        <button onClick={() => setCreating(true)} className="btn-primary text-sm px-4 py-2">
          + محصول جدید
        </button>
      </div>

      {/* نوار ابزار: جستجو + فیلتر موجودی/ویژه + فیلتر نوع کالا + نمایش غیرفعال‌ها */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        <div className="relative">
          <Search size={13} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="جستجوی محصول..."
            className="input-dark text-[11px]"
            style={{ width: '10rem', padding: '0.3rem 2rem 0.3rem 0.75rem' }} />
        </div>
        <select value={stockFilter} onChange={e => setStockFilter(e.target.value)}
          className="input-dark text-[11px]" style={{ width: '7.5rem', padding: '0.3rem 0.75rem' }}>
          <option value="">موجودی: همه</option>
          <option value="in">موجود</option>
          <option value="out">ناموجود</option>
          <option value="discontinued">توقف تولید</option>
        </select>
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" checked={onlyFeatured} onChange={e => setOnlyFeatured(e.target.checked)}
            className="w-3.5 h-3.5 accent-[#FBC02D]" />
          <span className="text-[11px] text-gray-steel">ویژه</span>
        </label>
        <select value={catFilter} onChange={e => { setCatFilter(e.target.value); setSubCatFilter('') }}
          className="input-dark text-[11px]" style={{ width: '9rem', padding: '0.3rem 0.75rem' }}>
          <option value="">دسته اصلی: همه</option>
          {rootCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        {subCatOptions.length > 0 && (
          <select value={subCatFilter} onChange={e => setSubCatFilter(e.target.value)}
            className="input-dark text-[11px]" style={{ width: '9rem', padding: '0.3rem 0.75rem' }}>
            <option value="">زیردسته: همه</option>
            {subCatOptions.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)}
            className="w-3.5 h-3.5 accent-[#FBC02D]" />
          <span className="text-[11px] text-gray-steel">نمایش غیرفعال‌ها (توقف تولید)</span>
        </label>
      </div>

      {isLoading ? <PageLoader /> : visibleProducts.length === 0 ? (
        <div className="text-center py-12 text-gray-steel text-sm">
          <Package size={36} className="mx-auto mb-3 opacity-40" />
          محصولی یافت نشد
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table style={{ width: '100%', minWidth: 640, borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid var(--color-border-strong)' }}>
                {['#', 'نام محصول', 'دسته', 'مدل', 'موجودی', 'وضعیت', 'ویژه'].map(h => (
                  <th key={h} style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 12 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleProducts.map((p, i) => (
                <tr key={p.id} style={{ borderBottom: '0.5px solid var(--color-border)', background: i % 2 ? 'var(--color-brand-softer)' : 'transparent', opacity: p.is_active ? 1 : 0.45 }}>
                  <td style={{ padding: '10px 8px', color: 'var(--color-text-muted)', fontSize: 11, width: 34 }}>{(i + 1).toLocaleString('fa-IR')}</td>
                  <td style={{ padding: '10px 14px', fontWeight: 600 }}>
                    <button onClick={() => setEditing(p.id)} className="hover:text-gold transition-colors text-right" title="ویرایش">
                      {p.name}
                    </button>
                  </td>
                  <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{p.category_name || '—'}</td>
                  <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }} dir="ltr">{p.model_number || '—'}</td>
                  <td style={{ padding: '10px 14px' }}>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={(p.total_stock ?? p.available_stock) > 0 ? 'badge-green' : 'badge-red'}>
                        {Number(p.total_stock ?? p.available_stock ?? 0).toLocaleString('fa-IR')}
                      </span>
                      {/* وضعیت موجودی و تفکیک انبار — سمت چپ عدد موجودی کلی */}
                      {p.availability === 'coming_soon' && <span className="badge-blue">به‌زودی</span>}
                      {p.availability === 'discontinued' && <span className="badge-red">توقف تولید</span>}
                      <StockChips stocks={p.stocks} />
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <span className={p.is_active ? 'badge-green' : 'badge-red'}>{p.is_active ? 'فعال' : 'غیرفعال'}</span>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    {p.is_featured && <span className="badge-gold badge">ویژه</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && <ProductEditor productId={editing} categories={categories} onClose={() => setEditing(null)} />}
      {creating && (
        <NewProductModal categories={categories}
          onCreated={(id) => { setCreating(false); setEditing(id) }}
          onClose={() => setCreating(false)} />
      )}
    </div>
  )
}
