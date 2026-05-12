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
function BoardFilters({ filters, set }) {
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
      <Section title="نام سنسور" defaultOpen={false}>
        <input value={filters.sensor_name || ''}
          onChange={e => set('sensor_name', e.target.value)}
          placeholder="مثال: IMX335، SC2310..."
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

// ─── لنز دوربین ───────────────────────────────────────────────────────────────
function LensFilters({ filters, set }) {
  const FOCAL_LENGTHS = ['1.7mm','1.8mm','2.8mm','3.6mm','4mm','6mm','8mm','12mm','16mm']
  const LENS_TYPES = ['فیکس','وریفکال','فیش آی','پین هولد','موتورایز']

  return (
    <>
      <Section title="فاصله کانونی">
        <div className="flex flex-wrap gap-1.5">
          {FOCAL_LENGTHS.map(f => (
            <FilterChip key={f}
              active={filters.focal_length === f}
              onClick={() => set('focal_length', filters.focal_length === f ? '' : f)}>
              {f}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="نوع لنز" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {LENS_TYPES.map(t => (
            <FilterChip key={t}
              active={filters.lens_type === t}
              onClick={() => set('lens_type', filters.lens_type === t ? '' : t)}>
              {t}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="نوع کاربرد" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['معمولی', 'استارلایت', 'دارک لایت'].map(u => (
            <FilterChip key={u}
              active={filters.lens_usage === u}
              onClick={() => set('lens_usage', filters.lens_usage === u ? '' : u)}>
              {u}
            </FilterChip>
          ))}
        </div>
      </Section>
      <Section title="رزولوشن" defaultOpen={false}>
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
      <Section title="نوع بدنه" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {['Bullet','Dome','Box','PTZ','Fisheye'].map(t => (
            <FilterChip key={t}
              active={filters.housing_type === t}
              onClick={() => set('housing_type', filters.housing_type === t ? '' : t)}>
              {t}
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

// ─── پنل اصلی ────────────────────────────────────────────────────────────────
export default function FilterPanel({ filters, onChange }) {
  const set = (key, val) => onChange({ ...filters, [key]: val })

  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: catalogService.getCategories,
  })
  const categories = Array.isArray(categoriesData)
    ? categoriesData
    : (categoriesData?.results || [])

  const selectedCat = categories.find(c => String(c.id) === String(filters.category))
  const catType = selectedCat?.category_type || ''

  const handleCategoryChange = (catId) => {
    onChange({
      category: catId,
      brand: filters.brand || '',
      search: filters.search || '',
      in_stock: filters.in_stock || '',
    })
  }

  return (
    <aside className="card p-4 h-fit sticky top-24">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-sm">فیلتر محصولات</h2>
        <button onClick={() => onChange({})}
          className="text-xs text-gray-steel hover:text-alert-red transition-colors">
          پاک کردن
        </button>
      </div>

      {/* دسته‌بندی */}
      <Section title="دسته‌بندی">
        <div className="flex flex-col gap-1.5">
          <FilterChip active={!filters.category} onClick={() => handleCategoryChange('')}>
            همه محصولات
          </FilterChip>
          {categories.map(cat => (
            <FilterChip key={cat.id}
              active={filters.category === String(cat.id)}
              onClick={() => handleCategoryChange(String(cat.id))}>
              {cat.name}
            </FilterChip>
          ))}
        </div>
      </Section>

      {/* فیلترهای اختصاصی */}
      {catType === 'board'   && <BoardFilters   filters={filters} set={set} />}
      {catType === 'lens'    && <LensFilters    filters={filters} set={set} />}
      {catType === 'modem'   && <ModemFilters   filters={filters} set={set} />}
      {catType === 'housing' && <HousingFilters filters={filters} set={set} />}

      {/* فیلترهای عمومی */}
      <Section title="شرکت سازنده" defaultOpen={false}>
        <input value={filters.brand || ''}
          onChange={e => set('brand', e.target.value)}
          placeholder="مثال: Sony، Hikvision..."
          className="input text-sm" />
      </Section>

      <Section title="جستجو" defaultOpen={false}>
        <input value={filters.search || ''}
          onChange={e => set('search', e.target.value)}
          placeholder="نام، مدل، ویژگی..."
          className="input text-sm" />
      </Section>

      <Section title="موجودی" defaultOpen={false}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox"
            checked={filters.in_stock === 'true'}
            onChange={e => set('in_stock', e.target.checked ? 'true' : '')}
            className="w-4 h-4 rounded border-gray-300 text-brand focus:ring-brand" />
          <span className="text-sm text-gray-700 dark:text-gray-300">فقط موجود</span>
        </label>
      </Section>
    </aside>
  )
}
