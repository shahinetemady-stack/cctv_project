import { SearchIcon } from './icons'

// ─── باکس جستجو (دسکتاپ + شیت موبایل) ─────────────────────────
// props:
//   value, onChange, onSubmit — منطق جستجو در Header
//   inputId — برای شورتکات ⌘K روی نسخه دسکتاپ
//   autoFocus — برای شیت موبایل
//   end — محتوای سمت چپ ورودی (kbd در دسکتاپ / دکمه ثبت در موبایل)
export default function SearchBox({ value, onChange, onSubmit, inputId, autoFocus = false, className = '', end = null }) {
  return (
    <form onSubmit={onSubmit} className={className}>
      <div className="relative flex items-center">
        <SearchIcon className="absolute right-3.5 text-[var(--color-text-muted)] pointer-events-none" />
        <input
          id={inputId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="جستجو در قطعات... (سنسور، چیپست، مدل)"
          autoFocus={autoFocus}
          className="w-full rounded-full border border-[var(--color-border)] bg-[var(--color-bg-elevated)] py-2 pr-10 pl-12 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] transition-colors focus:outline-none focus:border-[var(--color-brand)] focus:shadow-[0_0_0_3px_var(--color-brand-soft)]"
        />
        {end && <div className="absolute left-3 flex items-center">{end}</div>}
      </div>
    </form>
  )
}
