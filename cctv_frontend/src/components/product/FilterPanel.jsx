import { useState } from 'react'
import clsx from 'clsx'

const PART_TYPES = [
  { value: '', label: 'همه' },
  { value: 'sensor', label: 'سنسور' },
  { value: 'lens',   label: 'لنز' },
  { value: 'board',  label: 'برد' },
  { value: 'isp',    label: 'ISP' },
  { value: 'housing',label: 'کیس' },
  { value: 'ir_cut', label: 'IR-Cut' },
  { value: 'motor',  label: 'موتور' },
  { value: 'fpc',    label: 'کابل FPC' },
  { value: 'power',  label: 'منبع تغذیه' },
  { value: 'other',  label: 'سایر' },
]
const LENS_MOUNTS = [
  { value: '', label: 'همه' },
  { value: 'm12', label: 'M12 (S-Mount)' },
  { value: 'cs',  label: 'CS-Mount' },
  { value: 'c',   label: 'C-Mount' },
  { value: 'm16', label: 'M16' },
  { value: 'none',label: 'بدون مانت' },
]
const VOLTAGES = ['3.3V', '5V', '12V DC', 'PoE', '24V AC']

function FilterChip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'text-xs px-3 py-1.5 rounded-lg border transition-all duration-150',
        active
          ? 'bg-brand text-white border-brand shadow-brand'
          : 'border-gray-200 dark:border-white/10 text-gray-600 dark:text-gray-400 hover:border-brand/50 hover:text-brand'
      )}
    >
      {children}
    </button>
  )
}

function Section({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="py-4 border-b border-gray-100 dark:border-white/5 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full text-sm font-semibold
          text-gray-800 dark:text-gray-200 mb-3"
      >
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

export default function FilterPanel({ filters, onChange }) {
  const set = (key, val) => onChange({ ...filters, [key]: val })

  return (
    <aside className="card p-4 h-fit sticky top-24">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-sm">فیلتر محصولات</h2>
        <button
          onClick={() => onChange({})}
          className="text-xs text-gray-steel hover:text-alert-red transition-colors"
        >
          پاک کردن همه
        </button>
      </div>

      {/* نوع قطعه */}
      <Section title="نوع قطعه">
        <div className="flex flex-wrap gap-1.5">
          {PART_TYPES.map(t => (
            <FilterChip
              key={t.value}
              active={filters.part_type === t.value}
              onClick={() => set('part_type', t.value)}
            >
              {t.label}
            </FilterChip>
          ))}
        </div>
      </Section>

      {/* مانت لنز */}
      <Section title="مانت لنز">
        <div className="flex flex-wrap gap-1.5">
          {LENS_MOUNTS.map(m => (
            <FilterChip
              key={m.value}
              active={filters.lens_mount === m.value}
              onClick={() => set('lens_mount', m.value)}
            >
              {m.label}
            </FilterChip>
          ))}
        </div>
      </Section>

      {/* ولتاژ */}
      <Section title="ولتاژ">
        <div className="flex flex-wrap gap-1.5">
          <FilterChip active={!filters.voltage} onClick={() => set('voltage', '')}>همه</FilterChip>
          {VOLTAGES.map(v => (
            <FilterChip key={v} active={filters.voltage === v} onClick={() => set('voltage', v)}>
              {v}
            </FilterChip>
          ))}
        </div>
      </Section>

      {/* چیپست */}
      <Section title="چیپست">
        <input
          value={filters.chipset || ''}
          onChange={e => set('chipset', e.target.value)}
          placeholder="مثال: IMX307، Hi3516..."
          className="input text-sm"
        />
      </Section>

      {/* فقط موجود */}
      <Section title="وضعیت موجودی" defaultOpen={false}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.in_stock === 'true'}
            onChange={e => set('in_stock', e.target.checked ? 'true' : '')}
            className="w-4 h-4 rounded border-gray-300 text-brand focus:ring-brand"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">فقط محصولات موجود</span>
        </label>
      </Section>
    </aside>
  )
}
