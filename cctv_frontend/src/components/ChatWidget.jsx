import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import useAuthStore from '../store/useAuthStore'
import { StaffChatPanel } from './SupportChatWidget'

// ─── ویجت چت دستیار هوشمند (موتورهای ابری + Qwen لوکال پشتیبان) ─────────────
// نام موتورها برای نمایش به ادمین
const ENGINE_NAMES = {
  gemini: 'Gemini', modelscope: 'ModelScope Qwen3', zai: 'z.ai GLM', deepseek: 'DeepSeek', qwen: 'Qwen لوکال',
}

export default function ChatWidget() {
  const isAdmin = useAuthStore(s => s.isAdmin)
  const user = useAuthStore(s => s.user)
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState('bot')   // 'bot' = ربات هوشمند | 'staff' = گفتگو با پرسنل
  const [engineName, setEngineName] = useState('')  // موتور اصلی — فقط برای ادمین
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'سلام! من لنزو هستم، دستیار هوشمند بازرگانی دوربینکار. درباره محصولات، قیمت یا انتخاب تجهیزات سؤال دارید؟' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const botListRef = useRef(null)

  // حالت «پرسنل» برای همه کاربران لاگین‌شده — مشتری با پشتیبانی، پرسنل هم با هم (و با ادمین)
  // چت می‌کنند؛ پرسنل در نقش «پاسخ‌دهنده» از پنل ادمین استفاده می‌کند.
  const canStaffChat = !!user
  // بج پاسخ‌های خوانده‌نشده پرسنل روی دکمه شناور (پول ۶۰ثانیه)
  const { data: unreadData } = useQuery({
    queryKey: ['chat-unread'],
    queryFn: () => api.get('/chat/mine/unread/').then(r => r.data),
    refetchInterval: 60000,
    enabled: canStaffChat,
  })
  const staffUnread = (open && mode === 'staff') ? 0 : (unreadData?.unread || 0)

  // فقط داخل کانتینر پیام‌ها اسکرول شود — scrollIntoView کل صفحه را هم جابه‌جا می‌کرد
  useEffect(() => {
    const el = botListRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, loading, open])

  // موتور اصلی ربات — فقط برای ادمین و فقط وقتی چت باز می‌شود
  useEffect(() => {
    if (!open || !isAdmin()) return
    api.get('/assistant/settings/')
      .then(({ data }) => setEngineName(ENGINE_NAMES[data.provider] || ''))
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // موتور واقعی آخرین پاسخ — اگر فالبک اتفاق افتاده باشد با موتور اصلی فرق می‌کند
  const lastActualEngine = [...messages].reverse().find(m => m.engine && m.engine !== 'rules')?.engine
  const headerEngine = lastActualEngine ? ENGINE_NAMES[lastActualEngine] : engineName

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    const next = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setInput('')
    setLoading(true)
    try {
      const { data } = await api.post('/assistant/chat/', {
        message: text,
        history: next.slice(-7, -1),
      }, { timeout: 130000 })
      setMessages(m => [...m, { role: 'assistant', content: data.reply, products: data.products, engine: data.engine, elapsed: data.elapsed }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: 'متأسفم، الان نتوانستم پاسخ بدهم. کمی بعد دوباره تلاش کنید.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* دکمه شناور */}
      <button
        id="chat-fab"
        onClick={() => setOpen(o => !o)}
        aria-label="دستیار هوشمند"
        className="chat-fab"
        style={{
          position: 'fixed', left: 16, zIndex: 60,
          width: 52, height: 52, borderRadius: '50%', border: 'none', cursor: 'pointer',
          background: 'var(--color-brand)', color: '#000', fontSize: 24,
          boxShadow: '0 4px 14px rgba(0,0,0,0.35)',
        }}>
        {open ? '✕' : '💬'}
        {staffUnread > 0 && (
          <span style={{
            position: 'absolute', top: -4, right: -4, minWidth: 20, height: 20, padding: '0 5px',
            borderRadius: 10, background: '#ef4444', color: '#fff', fontSize: 11, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {staffUnread.toLocaleString('fa-IR')}
          </span>
        )}
      </button>

      {/* پنل چت */}
      {open && (
        <div className="chat-panel" style={{
          position: 'fixed', left: 16, zIndex: 60,
          width: 340, maxWidth: 'calc(100vw - 32px)', height: 440, maxHeight: '60vh',
          display: 'flex', flexDirection: 'column', borderRadius: 14, overflow: 'hidden',
          background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
          boxShadow: '0 10px 30px rgba(0,0,0,0.4)',
        }}>
          <div className="px-4 py-3 text-sm font-bold flex items-center justify-between" style={{ background: 'var(--color-bg-secondary)', borderBottom: '1px solid var(--color-border)' }}>
            <span>{mode === 'bot' ? '🤖 لنزو — بازرگانی دوربینکار' : '👤 گفتگو با پرسنل'}</span>
            {/* نام موتور (اصلی یا موتور واقعی آخرین پاسخ) — فقط برای ادمین و در حالت ربات */}
            {mode === 'bot' && isAdmin() && headerEngine && (
              <span className="text-[10px] font-normal px-2 py-0.5 rounded-full" style={{ background: 'var(--color-brand)', color: '#000' }}>
                {headerEngine}
              </span>
            )}
          </div>

          {/* سلکتور حالت: ربات هوشمند / پرسنل — فقط کاربر لاگین‌شده غیرپرسنل */}
          {canStaffChat && (
            <div className="flex text-[11px]" style={{ borderBottom: '1px solid var(--color-border)' }}>
              {[['bot', '🤖 ربات هوشمند'], ['staff', '👤 پرسنل']].map(([k, label]) => (
                <button key={k} onClick={() => setMode(k)}
                  className="flex-1 py-1.5 transition-colors"
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: mode === k ? 'var(--color-brand)' : 'var(--color-text-secondary)',
                    borderBottom: mode === k ? '2px solid var(--color-brand)' : '2px solid transparent',
                    fontWeight: mode === k ? 700 : 400,
                  }}>
                  {label}
                </button>
              ))}
            </div>
          )}

          {mode === 'staff' && canStaffChat ? (
            <StaffChatPanel />
          ) : (
          <>
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2" ref={botListRef}>
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
                {/* نشان موتور پاسخ — خوانا و ثابت زیر جواب، فقط برای ادمین */}
                {isAdmin() && m.role === 'assistant' && m.engine && m.engine !== 'rules' && (
                  <div className="mt-1">
                    <span className="inline-block text-[11px] font-semibold px-2.5 py-1 rounded-lg"
                      style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-brand)', color: 'var(--color-brand)' }}>
                      {{ gemini: '⚡ Gemini', modelscope: '☁️ ModelScope Qwen3', zai: '☁️ z.ai GLM', deepseek: '☁️ DeepSeek', qwen: '🖥 Qwen لوکال' }[m.engine] || m.engine}
                      {m.elapsed != null && ` — ${Number(m.elapsed).toLocaleString('fa-IR')} ثانیه`}
                    </span>
                  </div>
                )}
                {m.products?.length > 0 && (
                  <div className="mt-1 space-y-1">
                    {m.products.slice(0, 4).map((p, j) => (
                      <Link key={j} to={p.url} onClick={() => setOpen(false)}
                        className="block px-3 py-1.5 rounded-lg text-xs"
                        style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}>
                        {/* نام و قیمت در دو خط جدا — مدل لاتین وسط متن فارسی چیدمان RTL را به‌هم می‌ریزد */}
                        <div>📷 {p.name}</div>
                        <div style={{ marginTop: 2, color: 'var(--color-brand)', fontWeight: 700 }}>
                          {p.price_irt ? `${Number(p.price_irt).toLocaleString('fa-IR')} ریال` : ''}
                          {!p.in_stock && <span style={{ color: '#e74c3c', fontWeight: 400 }}> (ناموجود)</span>}
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="text-xs px-2" style={{ color: 'var(--color-text-secondary)' }}>
                {isAdmin() && engineName ? `در حال پاسخ با ${engineName}… ⏳` : 'در حال فکر کردن… ⏳'}
              </div>
            )}
          </div>

          <div className="flex gap-2 p-2" style={{ borderTop: '1px solid var(--color-border)' }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && send()}
              placeholder="سؤالتان را بنویسید…"
              className="flex-1 px-3 py-2 rounded-lg text-xs outline-none"
              style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}
            />
            <button onClick={send} disabled={loading}
              className="px-4 py-2 rounded-lg text-xs font-bold"
              style={{ background: 'var(--color-brand)', color: '#000', border: 'none', cursor: 'pointer', opacity: loading ? 0.5 : 1 }}>
              ارسال
            </button>
          </div>
          </>
          )}
        </div>
      )}
    </>
  )
}
