import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { catalogService } from '../../services/catalog'
import clsx from 'clsx'

function FilterChip({ active, onClick, children }) {
  return (
    <button onClick={onClick}
      className={clsx(
        'text-xs px-3 py-1.5 rounded-lg border transition-all duration-150',
        active
          ? 'bg-brand text-white border-brand shadow-brand'
          : 'border-gray-200 dark:border-white/10 text-gray-600 dark:text-gray-400 hover:border-brand/50 hover:text-brand'
      )}>
      {children}
    </button>
  )
}

function Section({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="py-3 border-b border-gray-100 dark:border-white/5 last:border-0">
      <button onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
        {title}
        <svg className={clsx('w-4 h-4 text-gray-steel transition-transform', open && 'rotate-180')}
          fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && children}
    </div>
  )
}

// ─── برد دوربین ───────────────────────────────────────────────────────────────
function BoardFilters({ filters, set, brandSection }) {
  return (
    <>
      <Section title="سیستم">
        <div className="flex flex-wrap gap-1.5">
          {['AHD', 'IP'].map(s => (
            <FilterChip key={s}
              active={filters.board_system === s}
              onClick={() => set('board_system', filters.board_system === s ? '' : s)}>
              {s}
            </FilterChip>
          ))}
        </div>
      </Section>
      {brandSection}
      <Section title="نام سنسور" defaultOpen={false}>
        <input value={filters.sensor_name || ''}
          onChange={e => set('sensor_name', e.target.value)}
          placeholder="مثال: IMX335، GC4653..."
          className="input text-sm" />
      </Section>
      <Section title="مدل پردازنده (ISP)" defaultOpen={false}>
        <input value={filters.ai_processor || ''}
          onChange={e => set('ai_processor', e.target.value)}
          placeholder="مثال: FH8536H، Fullhan..."
          className="input text-sm" />
      </Section>
      <Section title="رزولوشن" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['2MP','4MP','5MP','8MP','12MP'].map(r => (
            <FilterChip key={r}
              active={filters.board_resolution === r}
              onClick={() => set('board_resolution', filters.board_resolution === r ? '' : r)}>
              {r}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="اندازه سنسور" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['1/4"','1/3"','1/2.8"','1/2.7"','1/2"','1/1.8"'].map(s => (
            <FilterChip key={s}
              active={filters.sensor_size === s}
              onClick={() => set('sensor_size', filters.sensor_size === s ? '' : s)}>
              {s}
            </FilterChip>
          ))}
        </div>
      </Section>
    </>
  )
}

// ─── لنز دوربین — گزینه‌ها مطابق ویرایشگر کاتالوگ (AdminProductsPage) ────────
function LensFilters({ filters, set }) {
  return (
    <>
      <Section title="فاصله کانونی">
        <div className="flex flex-wrap gap-1.5">
          {['1.7mm','1.8mm','2.8mm','3.6mm','4mm','6mm','8mm','12mm','16mm'].map(f => (
            <FilterChip key={f}
              active={filters.lens_degree === f}
              onClick={() => set('lens_degree', filters.lens_degree === f ? '' : f)}>
              {f}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="رزولوشن لنز" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['3MP', '5MP', '8MP'].map(r => (
            <FilterChip key={r}
              active={filters.lens_resolution === r}
              onClick={() => set('lens_resolution', filters.lens_resolution === r ? '' : r)}>
              {r}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="ضریب دیافراگم" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['F1.0','F1.2','F1.4','F1.6','F2.0'].map(a => (
            <FilterChip key={a}
              active={filters.lens_aperture === a}
              onClick={() => set('lens_aperture', filters.lens_aperture === a ? '' : a)}>
              {a}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="مانت / رزوه" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['M12','D14','CS-Mount'].map(m => (
            <FilterChip key={m}
              active={filters.lens_mount === m}
              onClick={() => set('lens_mount', filters.lens_mount === m ? '' : m)}>
              {m}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="کلاس نوری" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['معمولی IR','استارلایت Starlight','دارکلایت Darklight','پلاک‌خوان LPR'].map(u => (
            <FilterChip key={u}
              active={filters.focal_ratio === u}
              onClick={() => set('focal_ratio', filters.focal_ratio === u ? '' : u)}>
              {u}
            </FilterChip>
          ))}
        </div>
      </Section>
    </>
  )
}

// ─── متعلقات ──────────────────────────────────────────────────────────────────
function ModemFilters({ filters, set }) {
  return (
    <>
      <Section title="نوع">
        <div className="flex flex-wrap gap-1.5">
          {['4G LTE','WiFi','PoE','RS485','RS232'].map(t => (
            <FilterChip key={t}
              active={filters.modem_type === t}
              onClick={() => set('modem_type', filters.modem_type === t ? '' : t)}>
              {t}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="ولتاژ" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['5V','12V DC','24V AC','PoE','48V'].map(v => (
            <FilterChip key={v}
              active={filters.voltage === v}
              onClick={() => set('voltage', filters.voltage === v ? '' : v)}>
              {v}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="قابلیت سیم کارت" defaultOpen={false}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox"
            checked={filters.sim_card === 'true'}
            onChange={e => set('sim_card', e.target.checked ? 'true' : '')}
            className="w-4 h-4 rounded border-gray-300 text-brand focus:ring-brand" />
          <span className="text-sm text-gray-700 dark:text-gray-300">دارای سیم کارت</span>
        </label>
      </Section>
    </>
  )
}

// ─── بدنه دوربین ──────────────────────────────────────────────────────────────
function HousingFilters({ filters, set }) {
  return (
    <>
      <Section title="جنس بدنه">
        <div className="flex flex-wrap gap-1.5">
          {['فلز', 'پلاستیک', 'فلز و پلاستیک'].map(m => (
            <FilterChip key={m}
              active={filters.housing_material === m}
              onClick={() => set('housing_material', filters.housing_material === m ? '' : m)}>
              {m}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="قابلیت میکروفون" defaultOpen={false}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox"
            checked={filters.has_microphone === 'true'}
            onChange={e => set('has_microphone', e.target.checked ? 'true' : '')}
            className="w-4 h-4 rounded border-gray-300 text-brand focus:ring-brand" />
          <span className="text-sm text-gray-700 dark:text-gray-300">دارای میکروفون</span>
        </label>
      </Section>
    </>
  )
}

// ─── فیلتر پویای یک ویژگی دسته (CategorySpecField) ────────────────────────────
function SpecFieldFilter({ field, filters, set }) {
  const paramKey = `spec_${field.key}`
  const value = filters[paramKey] || ''

  return (
    <Section title={field.label} defaultOpen={false}>
      {field.field_type === 'checkbox' ? (
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox"
            checked={value === 'true'}
            onChange={e => set(paramKey, e.target.checked ? 'true' : '')}
            className="w-4 h-4 rounded border-gray-300 text-brand focus:ring-brand" />
          <span className="text-sm text-gray-700 dark:text-gray-300">دارد</span>
        </label>
      ) : field.field_type === 'select' && field.choices ? (
        <div className="flex flex-wrap gap-1.5">
          {field.choices.split(',').map(c => c.trim()).filter(Boolean).map(c => (
            <FilterChip key={c}
              active={value === c}
              onClick={() => set(paramKey, value === c ? '' : c)}>
              {c}
            </FilterChip>
          ))}
        </div>
      ) : (
        <input value={value}
          onChange={e => set(paramKey, e.target.value)}
          placeholder={field.label}
          className="input text-sm" />
      )}
    </Section>
  )
}

// پیدا کردن دسته (ریشه یا فرزند) در درخت
function findCategory(list, id) {
  for (const c of list) {
    if (String(c.id) === String(id)) return c
    const found = findCategory(c.children || [], id)
    if (found) return found
  }
  return null
}

// ─── پنل اصلی ────────────────────────────────────────────────────────────────
export default function FilterPanel({ filters, onChange }) {
  const set = (key, val) => onChange({ ...filters, [key]: val })

  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: catalogService.getCategories,
  })
  const allCategories = Array.isArray(categoriesData)
    ? categoriesData
    : (categoriesData?.results || [])
  const selectedCat = filters.category ? findCategory(allCategories, filters.category) : null
  const parentCat = selectedCat?.parent ? findCategory(allCategories, selectedCat.parent) : null
  const catType = selectedCat?.category_type || parentCat?.category_type || ''
  // فقط دسته‌های اصلی (ریشه) برای انتخاب اولیه
  const rootCategories = allCategories.filter(c => !c.parent)

  // ویژگی‌های دسته: از ریشه + خود دسته (در صورت انتخاب زیردسته)
  // فقط تیک‌خورده‌ها (is_filterable) در پنل فیلتر می‌آیند — بقیه فقط در مشخصات محصول دیده می‌شوند
  const specFields = [
    ...(parentCat?.spec_fields || []),
    ...(selectedCat?.spec_fields || []),
  ].filter(f => f.is_filterable !== false)

  // برندها فقط از دسته اصلی انتخاب‌شده — از API دسته‌ها می‌آید پس با مدیریت
  // «ویژگی‌های دسته‌ها» همیشه سینک است (افزودن/ویرایش/حذف خودکار اعمال می‌شود)
  const brands = (parentCat || selectedCat)?.brands || []

  // تغییر دسته اصلی — بقیه فیلترهای اختصاصی ریست می‌شوند
  const handleCategoryChange = (catId) => {
    onChange({
      category: catId,
      brand: filters.brand || '',
      search: filters.search || '',
      in_stock: filters.in_stock || '',
      discounted: filters.discounted || '',
      ordering: filters.ordering || '',
    })
  }

  // دراپ‌داون برند — برای برد دقیقاً زیر «سیستم» قرار می‌گیرد، برای بقیه دسته‌ها بالای فیلترهایشان
  const brandSection = filters.category && brands.length > 0 && (
    <Section title="برند">
      <select value={filters.brand || ''}
        onChange={e => set('brand', e.target.value)}
        className="input text-sm w-full">
        <option value="">همه برندها</option>
        {brands.map(b => (
          <option key={b} value={b}>{b}</option>
        ))}
      </select>
    </Section>
  )

  return (
    <aside className="card p-4 sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-sm">فیلتر محصولات</h2>
        <button onClick={() => onChange({})}
          className="text-xs text-gray-steel hover:text-alert-red transition-colors">
          پاک کردن
        </button>
      </div>

      {/* موجودی + تخفیف — همیشه نمایان (بدون آکاردئون)، بالای لیست */}
      <div className="flex items-center gap-4 mb-4 pb-3 border-b border-[var(--color-border)]">
        <label className="flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
          <input type="checkbox"
            checked={filters.in_stock === 'true'}
            onChange={e => set('in_stock', e.target.checked ? 'true' : '')}
            className="w-3.5 h-3.5 rounded border-gray-300 text-brand focus:ring-brand" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">فقط موجود</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
          <input type="checkbox"
            checked={filters.discounted === 'true'}
            onChange={e => set('discounted', e.target.checked ? 'true' : '')}
            className="w-3.5 h-3.5 rounded border-gray-300 text-brand focus:ring-brand" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">فقط تخفیف‌دار</span>
        </label>
      </div>

      {/* مرتب‌سازی قیمت — همیشه نمایان (زیر فقط تخفیف‌دار) */}
      <div className="mb-4 pb-3 border-b border-[var(--color-border)]">
        <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">مرتب‌سازی قیمت</p>
        <div className="flex flex-wrap gap-1.5">
          <FilterChip
            active={filters.ordering === 'price'}
            onClick={() => set('ordering', filters.ordering === 'price' ? '' : 'price')}>
            از کم به زیاد
          </FilterChip>
          <FilterChip
            active={filters.ordering === '-price'}
            onClick={() => set('ordering', filters.ordering === '-price' ? '' : '-price')}>
            از زیاد به کم
          </FilterChip>
        </div>
      </div>

      {/* قدم اول: انتخاب دسته اصلی — فیلترهای ویژگی فقط بعد از انتخاب دسته ظاهر می‌شوند */}
      <div className="mb-2 pb-3 border-b border-[var(--color-border)]">
        <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
          دسته اصلی
        </label>
        <select
          value={selectedCat && !selectedCat.parent ? String(selectedCat.id) : (parentCat ? String(parentCat.id) : '')}
          onChange={e => handleCategoryChange(e.target.value)}
          className="input text-sm w-full">
          <option value="">انتخاب دسته...</option>
          {rootCategories.map(c => (
            <option key={c.id} value={String(c.id)}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* فیلترهای اختصاصی نوع دسته — فقط وقتی دسته انتخاب شده */}
      {filters.category && catType === 'board'   && <BoardFilters   filters={filters} set={set} brandSection={brandSection} />}
      {filters.category && catType !== 'board'   && brandSection}
      {filters.category && catType === 'lens'    && <LensFilters    filters={filters} set={set} />}
      {filters.category && catType === 'modem'   && <ModemFilters   filters={filters} set={set} />}
      {filters.category && catType === 'housing' && <HousingFilters filters={filters} set={set} />}

      {/* ویژگی‌های پویای دسته — از مدیریت «ویژگی‌های دسته‌ها» تعریف می‌شوند */}
      {filters.category && specFields.map(f => (
        <SpecFieldFilter key={f.key} field={f} filters={filters} set={set} />
      ))}
    </aside>
  )
}
