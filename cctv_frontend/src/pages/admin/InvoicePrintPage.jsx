import { useEffect, useRef } from 'react'

export default function InvoicePrintPage() {
  const loaded = useRef(false)

  useEffect(() => {
    if (loaded.current) return
    loaded.current = true

    const html = localStorage.getItem('invoice_print_html')
    if (!html) return

    localStorage.removeItem('invoice_print_html')

    // تغییر title
    const titleMatch = html.match(/<title>(.*?)<\/title>/)
    if (titleMatch) document.title = titleMatch[1]

    // اضافه کردن style‌ها به head فعلی
    const styleMatch = html.match(/<style>([\s\S]*?)<\/style>/)
    if (styleMatch) {
      const style = document.createElement('style')
      style.textContent = styleMatch[1]
      document.head.appendChild(style)
    }

    // استخراج body
    const bodyMatch = html.match(/<body>([\s\S]*?)<\/body>/)
    if (bodyMatch) {
      document.body.innerHTML = bodyMatch[1]
      document.body.style.margin = '0'
      document.body.style.padding = '0'
      document.body.style.background = '#fff'
    }

    // پرینت بعد از لود کامل
    setTimeout(() => window.print(), 800)
  }, [])

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', fontFamily: 'Vazirmatn, Tahoma', direction: 'rtl', color: '#666'
    }}>
      در حال آماده‌سازی فاکتور...
    </div>
  )
}
