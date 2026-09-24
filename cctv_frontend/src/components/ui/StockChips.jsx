// ─── چیپ‌های تفکیک موجودی انبار — زیر بج موجودی کلی (پنل ادمین) ──
// هر انبار یک چیپ فشرده: آیکون نوع انبار + تعداد + نام کوتاه.
// سبز = انبار «نمایش به مشتری» (موجودی قابل فروش) | کهربایی = داخلی/در راه 🔒
const TYPE_META = {
  shop1:       { icon: '🏪', label: 'فروشگاه ۱' },
  shop2:       { icon: '🏪', label: 'فروشگاه ۲' },
  air_transit: { icon: '✈️', label: 'هوایی' },
  sea_transit: { icon: '🚢', label: 'دریایی' },
  assembly:    { icon: '🔧', label: 'مونتاژ' },
}

export default function StockChips({ stocks, className = '' }) {
  if (!stocks?.length) return null
  return (
    <div className={`flex flex-wrap gap-1 ${className}`}>
      {stocks.map(s => {
        const meta = TYPE_META[s.warehouse_type] || { icon: '📦', label: s.warehouse }
        const pub = !!s.is_public
        return (
          <span key={s.warehouse}
            title={`${s.warehouse}${pub ? ' — نمایش به مشتری' : ' — بدون نمایش به مشتری 🔒'}`}
            className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] border whitespace-nowrap"
            style={pub
              ? { background: 'rgba(52,211,153,0.10)', borderColor: 'rgba(52,211,153,0.25)', color: '#34D399' }
              : { background: 'rgba(251,191,36,0.08)', borderColor: 'rgba(251,191,36,0.20)', color: '#FBBF24' }}>
            <span>{meta.icon}</span>
            <span className="font-bold">{Number(s.quantity).toLocaleString('fa-IR')}</span>
            <span className="opacity-75">{meta.label}</span>
          </span>
        )
      })}
    </div>
  )
}
