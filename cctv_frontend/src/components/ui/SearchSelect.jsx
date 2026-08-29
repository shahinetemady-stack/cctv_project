// سلکت با جستجو — برای انتخاب از لیست‌های بلند (طرف حساب، کالا)
// جستجو با نرمال‌سازی ارقام فارسی/عربی → لاتین و حروف عربی (ك/ي → ک/ی)
import { useState, useRef, useEffect } from 'react'

const normalize = (s) => String(s ?? '')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
  .replace(/ك/g, 'ک').replace(/ي/g, 'ی')
  .toLowerCase()

// پرش خودکار به فیلد بعدی در جریان فرم — فیلدهای data-flow مشترک به ترتیب DOM
export function advanceFlow(flow, el) {
  if (!flow || !el) return
  const fields = [...document.querySelectorAll(`[data-flow="${flow}"]`)]
    .filter(f => !f.disabled && f.offsetParent)
  const next = fields[fields.indexOf(el) + 1]
  if (next) { next.focus(); next.select?.() }
}

export default function SearchSelect({ options, value, onChange, placeholder = 'جستجو و انتخاب...', className = 'input text-sm', flow }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [activeIdx, setActiveIdx] = useState(-1)   // آیتم انتخاب‌شده با کیبورد (↑↓)
  const ref = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const selected = options.find(o => String(o.value) === String(value))
  const nq = normalize(q)
  const filtered = options
    .filter(o => !nq || normalize(o.label).includes(nq) || normalize(o.sub || '').includes(nq))
    .slice(0, 30)

  const pick = (o) => {
    onChange(o.value)
    setOpen(false)
    setActiveIdx(-1)
    advanceFlow(flow, inputRef.current)
  }

  const onKeyDown = (e) => {
    if (!open && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) { setOpen(true); setQ(''); return }
    if (!open) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx(i => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && activeIdx >= 0 && filtered[activeIdx]) {
      e.preventDefault()
      pick(filtered[activeIdx])
    } else if (e.key === 'Escape') {
      setOpen(false)
      setActiveIdx(-1)
    }
  }

  return (
    <div ref={ref} className="relative">
      <input
        ref={inputRef}
        data-flow={flow}
        value={open ? q : (selected?.label || '')}
        onFocus={() => { setOpen(true); setQ('') }}
        onChange={e => { setQ(e.target.value); setOpen(true); setActiveIdx(0) }}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        className={className}
        autoComplete="off"
      />
      {open && (
        <div className="absolute z-50 top-full right-0 left-0 mt-1 bg-navy border border-white/10 rounded-xl shadow-xl overflow-hidden max-h-60 overflow-y-auto">
          {filtered.map((o, i) => (
            <button key={o.value} type="button"
              onMouseDown={(e) => { e.preventDefault(); pick(o) }}
              onMouseEnter={() => setActiveIdx(i)}
              className={`w-full text-right px-4 py-2.5 border-b border-white/5 last:border-0 ${
                i === activeIdx ? 'bg-brand/20' : 'hover:bg-white/5'
              } ${String(o.value) === String(value) ? 'bg-brand/10' : ''}`}>
              <div className="text-sm text-white">{o.label}</div>
              {o.sub && <div className="text-[10px] text-gray-steel" dir="ltr">{o.sub}</div>}
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-4 text-gray-steel text-xs">نتیجه‌ای نیست</div>
          )}
        </div>
      )}
    </div>
  )
}
