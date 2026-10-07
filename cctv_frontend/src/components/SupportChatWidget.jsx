// اجزای مشترک چت پشتیبانی مشتری ↔ پرسنل
// StaffChatPanel داخل چت‌باکس موجود (ChatWidget — حالت «پرسنل») استفاده می‌شود؛
// ChatBubble/ChatComposer هم در صفحه ادمین چت به‌کار می‌روند.
import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { X, Paperclip, Send } from 'lucide-react'
import api from '../services/api'

const fmtTime = (iso) => new Date(iso).toLocaleString('fa-IR', {
  timeZone: 'Asia/Tehran', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
})

// فرم ارسال پیام — مشترک بین پنل مشتری و صفحه ادمین
export function ChatComposer({ onSend, placeholder = 'پیام خود را بنویسید...' }) {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [sending, setSending] = useState(false)
  const fileRef = useRef(null)

  const submit = async () => {
    if (!text.trim() && !file) return
    setSending(true)
    try {
      const fd = new FormData()
      if (text.trim()) fd.append('text', text.trim())
      if (file) fd.append('attachment', file)
      await onSend(fd)
      setText(''); setFile(null)
    } finally { setSending(false) }
  }

  return (
    <div className="border-t border-white/10 p-2">
      {file && (
        <div className="flex items-center gap-2 text-[11px] text-gray-steel mb-1.5 bg-white/5 rounded-lg px-2 py-1">
          <Paperclip size={12} />
          <span className="flex-1 truncate" dir="ltr">{file.name}</span>
          <button onClick={() => setFile(null)} className="text-red-400 hover:text-red-300"><X size={12} /></button>
        </div>
      )}
      <div className="flex items-end gap-1.5">
        <button onClick={() => fileRef.current?.click()} title="پیوست (عکس یا فایل)"
          className="p-2 text-gray-steel hover:text-brand transition-colors shrink-0">
          <Paperclip size={17} />
        </button>
        <input ref={fileRef} type="file" className="hidden"
          accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.zip,.rar,.txt,.doc,.docx,.xls,.xlsx"
          onChange={e => setFile(e.target.files?.[0] || null)} />
        <textarea value={text} onChange={e => setText(e.target.value)} rows={1}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
          placeholder={placeholder}
          className="input-dark text-xs flex-1 resize-none" style={{ minHeight: 34 }} />
        <button onClick={submit} disabled={sending || (!text.trim() && !file)}
          className="p-2 text-brand hover:text-cyan transition-colors disabled:opacity-40 shrink-0">
          <Send size={17} />
        </button>
      </div>
    </div>
  )
}

// حباب یک پیام — viewerIsStaff یعنی بیننده پرسنل است
export function ChatBubble({ m, viewerIsStaff }) {
  const isMine = m.from_staff === viewerIsStaff
  return (
    <div className={`flex ${isMine ? 'justify-start' : 'justify-end'} mb-2`}>
      <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-xs leading-5 ${
        isMine ? 'bg-brand/15 text-white rounded-br-sm' : 'text-gray-100 rounded-bl-sm'}`}
        style={isMine ? {} : { background: 'rgba(255,255,255,0.07)' }}>
        <div className="text-[9px] text-gray-steel mb-0.5">{m.from_staff ? 'پشتیبانی' : (m.sender_name || 'مشتری')}</div>
        {m.text && <div className="whitespace-pre-wrap break-words">{m.text}</div>}
        {m.attachment_url && (m.is_image ? (
          <a href={m.attachment_url} target="_blank" rel="noreferrer">
            <img src={m.attachment_url} alt={m.attachment_name}
              className="rounded-lg mt-1 max-h-44 max-w-full object-contain bg-black/30" loading="lazy" />
          </a>
        ) : (
          <a href={m.attachment_url} target="_blank" rel="noreferrer"
            className="flex items-center gap-1.5 mt-1 text-brand hover:underline" dir="ltr">
            <Paperclip size={12} /> {m.attachment_name || 'دانلود فایل'}
          </a>
        ))}
        <div className="text-[9px] text-gray-steel mt-1 text-left" dir="ltr">{fmtTime(m.created_at)}</div>
      </div>
    </div>
  )
}

// پنل کامل گفتگو با پرسنل — برای جاسازی در چت‌باکس موجود (حالت «پرسنل»)
export function StaffChatPanel() {
  const qc = useQueryClient()
  const [assigning, setAssigning] = useState(false)

  const { data: chat } = useQuery({
    queryKey: ['chat-mine'],
    queryFn: () => api.get('/chat/mine/').then(r => r.data),
    refetchInterval: 10000,
  })
  const { data: staffList = [] } = useQuery({
    queryKey: ['chat-staff-list'],
    queryFn: () => api.get('/chat/staff-list/').then(r => r.data),
    staleTime: 300000,
  })

  const messages = chat?.messages || []
  const listRef = useRef(null)
  // فقط داخل کانتینر پیام‌ها اسکرول شود — scrollIntoView کل صفحه را هم جابه‌جا می‌کرد
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages.length])
  useEffect(() => {
    qc.invalidateQueries(['chat-unread'])
  }, [messages.length])

  const assign = async (id) => {
    setAssigning(true)
    try {
      await api.post('/chat/mine/assign/', { assigned_to: id || null })
      qc.invalidateQueries(['chat-mine'])
    } finally { setAssigning(false) }
  }

  return (
    <>
      {/* انتخاب پرسنل گفتگو — خالی یعنی پشتیبانی عمومی (همه پرسنل می‌بینند) */}
      <div className="px-3 py-2 border-b border-white/10 flex items-center gap-2">
        <span className="text-[10px] text-gray-steel whitespace-nowrap">گفتگو با:</span>
        <select value={chat?.assigned_to ?? ''} disabled={assigning}
          onChange={e => assign(e.target.value ? Number(e.target.value) : null)}
          className="input-dark text-[11px] flex-1 py-1">
          <option value="">پشتیبانی (عمومی)</option>
          {staffList.map(s => (
            <option key={s.id} value={s.id}>{s.name}{s.role ? ` — ${s.role}` : ''}</option>
          ))}
        </select>
      </div>
      <div className="flex-1 overflow-y-auto p-3" ref={listRef}>
        {messages.length === 0 && (
          <div className="text-center text-gray-steel text-xs py-10">
            سلام! 👋 سؤال یا مشکلی دارید؟ پیام یا فایل بگذارید، پرسنل پاسخ می‌دهند.
          </div>
        )}
        {messages.map(m => <ChatBubble key={m.id} m={m} viewerIsStaff={false} />)}
      </div>
      <ChatComposer onSend={async (fd) => {
        await api.post('/chat/mine/', fd)
        qc.invalidateQueries(['chat-mine'])
      }} />
    </>
  )
}
