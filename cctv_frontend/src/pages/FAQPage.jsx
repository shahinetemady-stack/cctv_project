import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ChevronDown, MessageCircleQuestion } from 'lucide-react'
import api from '../services/api'

// ─── صفحه سوالات متداول — محتوا از پنل ادمین جنگو (پرسش‌های متداول) ───
export default function FAQPage() {
  const [openId, setOpenId] = useState(null)
  const { data: faqs = [], isLoading } = useQuery({
    queryKey: ['faqs'],
    queryFn: () => api.get('/assistant/faqs/').then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })

  return (
    <div className="container-main py-12 max-w-3xl">
      {/* هدر */}
      <div className="text-center mb-10">
        <div className="text-5xl mb-4">❓</div>
        <h1 className="font-display font-bold text-3xl text-white mb-3">سوالات متداول</h1>
        <p className="text-gray-steel text-sm max-w-md mx-auto">
          پاسخ پرتکرارترین سؤالات مشتریان را اینجا جمع کرده‌ایم. اگر جوابتان را پیدا نکردید، از دستیار هوشمند سایت بپرسید.
        </p>
      </div>

      {isLoading && (
        <div className="text-center text-gray-steel text-sm py-10">در حال بارگذاری…</div>
      )}

      {!isLoading && faqs.length === 0 && (
        <div className="text-center py-14 rounded-2xl border border-white/10 bg-white/5">
          <MessageCircleQuestion size={36} className="mx-auto mb-3 text-gray-steel" />
          <p className="text-gray-steel text-sm">به‌زودی سؤالات پرتکرار اینجا منتشر می‌شود.</p>
        </div>
      )}

      {/* آکاردئون سؤال‌ها */}
      <div className="space-y-3">
        {faqs.map((f) => {
          const open = openId === f.id
          return (
            <div key={f.id}
              className="rounded-2xl border overflow-hidden transition-colors"
              style={{
                borderColor: open ? 'var(--color-brand)' : 'var(--color-border)',
                background: 'var(--color-bg-elevated)',
              }}>
              <button
                onClick={() => setOpenId(open ? null : f.id)}
                className="w-full flex items-center justify-between gap-3 px-5 py-4 text-right cursor-pointer"
                style={{ background: 'transparent', border: 'none' }}>
                <span className="text-sm font-bold" style={{ color: 'var(--color-text-primary)' }}>{f.question}</span>
                <ChevronDown size={18}
                  style={{
                    color: 'var(--color-brand)', flexShrink: 0,
                    transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none',
                  }} />
              </button>
              {open && (
                <div className="px-5 pb-5 text-sm leading-8 whitespace-pre-wrap animate-fade-in"
                  style={{ color: 'var(--color-text-secondary)', borderTop: '1px solid var(--color-border)', paddingTop: 14 }}>
                  {f.answer}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* لینک بازگشت به سفارش از چین */}
      <div className="text-center mt-10">
        <Link to="/china-order" className="text-sm" style={{ color: 'var(--color-brand)', textDecoration: 'none' }}>
          ← صفحه سفارش مستقیم از چین
        </Link>
      </div>
    </div>
  )
}
