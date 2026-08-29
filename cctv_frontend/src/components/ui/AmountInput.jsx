// ورودی مبلغ با جداکننده سه‌رقمی — ارقام فارسی/عربی هم پذیرفته می‌شوند
// مقدار همیشه به‌صورت رشته خام (فقط رقم لاتین + . و -) در state ذخیره می‌شود
// و همان را از طریق onChange({ target: { value } }) پاس می‌دهد تا با هندلرهای فعلی سازگار بماند.

export function parseAmount(v) {
  return String(v ?? '')
    .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
    .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
    .replace(/[٬،,\s]/g, '')
    .replace(/(?!^)-/g, '')
    .replace(/[^\d.-]/g, '')
}

export function formatAmount(v) {
  const s = parseAmount(v)
  if (s === '' || s === '-') return s
  const [int, dec] = s.split('.')
  const sign = int.startsWith('-') ? '-' : ''
  const grouped = int.replace('-', '').replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return sign + grouped + (dec !== undefined ? '.' + dec : '')
}

export default function AmountInput({ value, onChange, ...props }) {
  return (
    <input
      type="text"
      inputMode="decimal"
      dir="ltr"
      {...props}
      value={formatAmount(value)}
      onChange={e => onChange && onChange({ target: { value: parseAmount(e.target.value) } })}
    />
  )
}
