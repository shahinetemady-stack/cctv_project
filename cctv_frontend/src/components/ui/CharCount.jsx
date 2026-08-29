// شمارنده کاراکتر فیلدهای سئو — سبز در بازه استاندارد، قرمز بیش از حد
export default function CharCount({ value, min, max }) {
  const n = String(value || '').trim().length
  const over = n > max
  const ok = !over && n >= min
  return (
    <div dir="ltr" className={`text-left text-[10px] mt-0.5 ${over ? 'text-red-400' : ok ? 'text-green-400' : 'text-gray-steel'}`}>
      {n.toLocaleString('fa-IR')}/{max.toLocaleString('fa-IR')}
      {over ? ' — بیش از حد مجاز!' : ok ? ' ✓' : ''}
    </div>
  )
}
