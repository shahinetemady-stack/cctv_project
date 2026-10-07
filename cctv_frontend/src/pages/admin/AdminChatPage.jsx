import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, Lock, LockOpen, Plus, X } from 'lucide-react'
import { toast } from 'sonner'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'
import { ChatBubble, ChatComposer } from '../../components/SupportChatWidget'

const fmtTime = (iso) => iso ? new Date(iso).toLocaleString('fa-IR', {
  timeZone: 'Asia/Tehran', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
}) : ''

const normalize = (s) => String(s ?? '')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
  .replace(/ك/g, 'ک').replace(/ي/g, 'ی').toLowerCase()

// ─── مودال شروع گفتگوی جدید توسط پرسنل ───
function NewChatModal({ onClose, onStarted }) {
  const [q, setQ] = useState('')
  const [picked, setPicked] = useState(null)
  const [sending, setSending] = useState(false)
  const { data: results = [] } = useQuery({
    queryKey: ['chat-user-search', q],
    queryFn: () => api.get('/chat/user-search/', { params: { q } }).then(r => r.data),
    enabled: q.trim().length >= 2 && !picked,
  })

  const start = async (fd) => {
    if (!picked) return toast.error('ابتدا مشتری را انتخاب کنید')
    setSending(true)
    try {
      fd.append('user_id', picked.id)
      const r = await api.post('/chat/conversations/start/', fd)
      toast.success(`پیام برای ${r.data.customer_name} ارسال شد`)
      onStarted({ id: r.data.conversation_id, customer_name: r.data.customer_name, is_closed: false })
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ارسال')
    } finally { setSending(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="card p-4 w-full max-w-md flex flex-col" style={{ maxHeight: '80vh' }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">شروع گفتگو با مشتری</h3>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={16} /></button>
        </div>
        {picked ? (
          <div className="flex items-center gap-2 bg-brand/10 border border-brand/30 rounded-lg px-3 py-2 mb-3">
            <span className="text-xs text-white flex-1">{picked.name} <span className="text-gray-steel" dir="ltr">{picked.phone}</span></span>
            <button onClick={() => setPicked(null)} className="text-gray-steel hover:text-red-400"><X size={13} /></button>
          </div>
        ) : (
          <div className="relative mb-3">
            <Search size={13} className="absolute top-2.5 text-[var(--color-text-muted)]" style={{ right: 8 }} />
            <input value={q} onChange={e => setQ(e.target.value)} autoFocus
              placeholder="جستجوی مشتری (نام یا موبایل)..." className="input-dark text-xs w-full" style={{ paddingRight: '1.75rem' }} />
            {results.length > 0 && (
              <div className="mt-1 card p-1 max-h-44 overflow-y-auto">
                {results.map(u => (
                  <button key={u.id} onClick={() => setPicked(u)}
                    className="w-full text-right px-2 py-1.5 rounded hover:bg-white/5 text-xs">
                    <span className="text-white">{u.name}</span>
                    {u.is_staff && (
                      <span className="text-[9px] mr-1.5 px-1.5 py-0.5 rounded-full bg-brand/10 text-brand">
                        پرسنل{u.role ? ` — ${u.role}` : ''}
                      </span>
                    )}
                    <span className="text-gray-steel mr-2" dir="ltr">{u.phone}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {picked && (
          <div className="flex-1 flex flex-col justify-end">
            <ChatComposer placeholder="اولین پیام به مشتری..." onSend={start} />
            {sending && <div className="text-[10px] text-gray-steel text-center">در حال ارسال...</div>}
          </div>
        )}
      </div>
    </div>
  )
}

export default function AdminChatPage() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState(null)   // { id, customer_name, is_closed }
  const [q, setQ] = useState('')
  const [showNew, setShowNew] = useState(false)
  const listRef = useRef(null)

  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ['chat-conversations'],
    queryFn: () => api.get('/chat/conversations/').then(r => r.data),
    refetchInterval: 15000,
  })
  const { data: thread } = useQuery({
    queryKey: ['chat-thread', selected?.id],
    queryFn: () => api.get(`/chat/conversations/${selected.id}/messages/`).then(r => r.data),
    refetchInterval: 10000,
    enabled: !!selected,
  })

  const messages = thread?.messages || []
  // فقط داخل کانتینر پیام‌ها اسکرول شود — scrollIntoView کل صفحه را هم جابه‌جا می‌کرد
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages.length, selected?.id])
  // خواندن رشته → بج لیست و منو به‌روز شود
  useEffect(() => {
    if (selected) qc.invalidateQueries(['chat-conversations'])
  }, [messages.length])

  const nq = normalize(q.trim())
  const filtered = conversations.filter(c =>
    !nq || normalize(c.customer_name).includes(nq) || normalize(c.customer_phone).includes(nq))

  const toggleClose = async () => {
    const r = await api.post(`/chat/conversations/${selected.id}/close/`)
    setSelected(s => ({ ...s, is_closed: r.data.is_closed }))
    qc.invalidateQueries(['chat-conversations'])
    qc.invalidateQueries(['chat-thread', selected.id])
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
        <h1 className="font-display font-bold text-2xl text-white">💬 چت مشتریان</h1>
        <button onClick={() => setShowNew(true)} className="btn-primary text-xs px-4 py-2 flex items-center gap-1">
          <Plus size={14} /> گفتگوی جدید
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4" style={{ height: 'min(75vh, 640px)' }}>
        {/* لیست گفتگوها */}
        <div className="card flex flex-col overflow-hidden">
          <div className="p-3 border-b border-white/10">
            <div className="relative">
              <Search size={13} className="absolute top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" style={{ right: 8 }} />
              <input value={q} onChange={e => setQ(e.target.value)} placeholder="جستجوی نام یا موبایل..."
                className="input-dark text-xs w-full" style={{ paddingRight: '1.75rem' }} />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 && (
              <div className="text-center text-gray-steel text-xs py-10">گفتگویی نیست</div>
            )}
            {filtered.map(c => (
              <button key={c.id}
                onClick={() => setSelected({ id: c.id, customer_name: c.customer_name, is_closed: c.is_closed })}
                className={`w-full text-right px-3 py-2.5 border-b border-white/5 transition-colors ${
                  selected?.id === c.id ? 'bg-brand/10' : 'hover:bg-white/5'}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-white truncate">{c.customer_name}</span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {c.assigned_to_name && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-brand/10 text-brand whitespace-nowrap">
                        👤 {c.assigned_to_name}
                      </span>
                    )}
                    {c.is_closed && <Lock size={11} className="text-gray-steel" />}
                    {c.unread > 0 && (
                      <span className="min-w-5 h-5 px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                        {c.unread.toLocaleString('fa-IR')}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between gap-2 mt-0.5">
                  <span className="text-[10px] text-gray-steel truncate">
                    {c.last_from_staff ? 'شما: ' : ''}{c.last_text || '—'}
                  </span>
                  <span className="text-[9px] text-gray-steel shrink-0" dir="ltr">{fmtTime(c.last_at)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* رشته پیام‌ها */}
        <div className="card md:col-span-2 flex flex-col overflow-hidden">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center text-gray-steel text-sm">
              یک گفتگو را انتخاب کنید
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/10 bg-white/5">
                <div className="text-xs font-bold text-white">
                  {selected.customer_name}
                  <span className="text-[10px] font-normal text-gray-steel mr-2">
                    {thread?.assigned_to_name ? `👤 اختصاص به ${thread.assigned_to_name}` : '🌐 عمومی — با اولین پاسخ، مالکیت آن را می‌گیرید'}
                  </span>
                </div>
                <button onClick={toggleClose}
                  className="flex items-center gap-1 text-[10px] text-gray-steel hover:text-white transition-colors">
                  {(thread?.is_closed ?? selected.is_closed)
                    ? <><LockOpen size={12} /> باز کردن گفتگو</>
                    : <><Lock size={12} /> بستن گفتگو</>}
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-3" ref={listRef}>
                {messages.map(m => <ChatBubble key={m.id} m={m} viewerIsStaff={true} />)}
              </div>
              <ChatComposer placeholder="پاسخ به مشتری..." onSend={async (fd) => {
                await api.post(`/chat/conversations/${selected.id}/messages/`, fd)
                qc.invalidateQueries(['chat-thread', selected.id])
                qc.invalidateQueries(['chat-conversations'])
              }} />
            </>
          )}
        </div>
      </div>

      {showNew && (
        <NewChatModal onClose={() => setShowNew(false)}
          onStarted={(conv) => {
            setShowNew(false)
            setSelected(conv)
            qc.invalidateQueries(['chat-conversations'])
          }} />
      )}
    </div>
  )
}
