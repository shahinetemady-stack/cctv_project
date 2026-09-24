import { useState, useRef, useEffect } from 'react'
import api from '../../services/api'

// ─── باکس راهنمای هوشمند حسابداری — فقط پنل مدیریت ───────────────────────────
// مشابه باکس هوشمند صفحه اصلی، ولی فقط به سؤالات نحوه کار با سیستم حسابداری
// جواب می‌دهد. اندپوینت IsAdminUser است — مشتریان به آن دسترسی ندارند.
const ENGINE_NAMES = {
  gemini: '⚡ Gemini', modelscope: '☁️ ModelScope Qwen3', zai: '☁️ z.ai GLM',
  deepseek: '☁️ DeepSeek', qwen: '🖥 Qwen لوکال',
}

const SUGGESTIONS = [
  'چطور هزینه پیک ثبت کنم؟',
  'پرداخت قسطی حقوق چطوریه؟',
  'مانده بدهی یک مشتری را از کجا ببینم؟',
  'سود سرمایه‌گذار چطور محاسبه می‌شود؟',
]

export default function AccountingChatBox() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'سلام! من راهنمای هوشمند حسابداری هستم 🤖 درباره نحوه کار با پنل (ثبت سند، فاکتور، کاردکس، حقوق، هزینه‌ها، گزارش‌ها و…) بپرسید.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const listRef = useRef(null)

  // فقط داخل لیست پیام‌ها اسکرول شود — scrollIntoView کل صفحه را به پایین می‌برد
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, loading])

  const send = async (text) => {
    text = (text ?? input).trim()
    if (!text || loading) return
    const next = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setInput('')
    setLoading(true)
    try {
      const { data } = await api.post('/assistant/accounting-chat/', {
        message: text,
        history: next.slice(-7, -1),
      }, { timeout: 130000 })
      setMessages(m => [...m, { role: 'assistant', content: data.reply, engine: data.engine, elapsed: data.elapsed }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: 'متأسفم، الان نتوانستم پاسخ بدهم. کمی بعد دوباره تلاش کنید.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card overflow-hidden">
      {/* سربرگ */}
      <div className="px-4 py-3 text-sm font-bold flex items-center justify-between"
        style={{ background: 'var(--color-bg-secondary)', borderBottom: '1px solid var(--color-border)' }}>
        <span>🤖 راهنمای هوشمند حسابداری</span>
        <span className="text-[10px] font-normal px-2 py-0.5 rounded-full bg-white/5 text-gray-steel">
          🔒 فقط پرسنل — پاسخ‌ها بر اساس راهنمای داخلی
        </span>
      </div>

      {/* پیام‌ها */}
      <div ref={listRef} className="overflow-y-auto px-3 py-3 space-y-2" style={{ height: 150 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ textAlign: m.role === 'user' ? 'left' : 'right' }}>
            <div className="inline-block px-3 py-2 rounded-xl text-xs leading-6 whitespace-pre-wrap"
              style={{
                maxWidth: '85%',
                background: m.role === 'user' ? 'var(--color-brand)' : 'var(--color-bg-secondary)',
                color: m.role === 'user' ? '#000' : 'var(--color-text-primary)',
              }}>
              {m.content}
            </div>
            {m.role === 'assistant' && m.engine && m.engine !== 'rules' && (
              <div className="mt-1">
                <span className="inline-block text-[11px] font-semibold px-2.5 py-1 rounded-lg"
                  style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-brand)', color: 'var(--color-brand)' }}>
                  {ENGINE_NAMES[m.engine] || m.engine}
                  {m.elapsed != null && ` — ${Number(m.elapsed).toLocaleString('fa-IR')} ثانیه`}
                </span>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="text-xs px-2" style={{ color: 'var(--color-text-secondary)' }}>در حال فکر کردن… ⏳</div>
        )}
      </div>

      {/* پیشنهادهای آماده — فقط وقتی هنوز سؤالی پرسیده نشده */}
      {messages.length === 1 && (
        <div className="flex flex-wrap gap-1.5 px-3 pb-2">
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => send(s)}
              className="text-[11px] px-2.5 py-1 rounded-full border border-white/10 text-gray-steel hover:text-white hover:border-brand/50 transition-colors">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* ورودی */}
      <div className="flex gap-2 p-2" style={{ borderTop: '1px solid var(--color-border)' }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="سؤالتان درباره کار با حسابداری…"
          className="flex-1 px-3 py-2 rounded-lg text-xs outline-none"
          style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <button onClick={() => send()} disabled={loading}
          className="px-4 py-2 rounded-lg text-xs font-bold"
          style={{ background: 'var(--color-brand)', color: '#000', border: 'none', cursor: 'pointer', opacity: loading ? 0.5 : 1 }}>
          ارسال
        </button>
      </div>
    </div>
  )
}
