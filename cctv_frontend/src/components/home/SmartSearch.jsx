import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, Bot, ArrowLeft, Sparkles, Loader2, Camera } from 'lucide-react'
import api from '../../services/api'
import { mediaUrl } from '../../utils/media'

// ─── چیپ‌های پیشنهادی (ترکیب جستجو + پرسش) ───────────────────
const CHIPS = [
  'لنز ۵ مگاپیکسل',
  'برد IP',
  'سنسور سونی',
  'کدام برد برای دوربین دام مناسبه؟',
  'لنز ۵ مگاپیکسل با چه سنسوری مچ می‌شه؟',
]

// ─── ابزار متن فارسی ──────────────────────────────────────────
const fa2en = (s) => s.replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
const faNum = (n) => Number(n).toLocaleString('fa-IR')

// ─── تحلیل سوال کاربر (فارسی + انگلیسی) ───────────────────────
function analyze(q) {
  const t = fa2en(q).toLowerCase()
  const mp = (t.match(/(\d+)\s*(?:مگاپیکسل|مگا|mp|megapixel)/) || [])[1]
  const parts = []
  if (/لنز|lens/.test(t)) parts.push('لنز')
  if (/برد|board|pcb|module|ماژول/.test(t)) parts.push('برد')
  if (/سنسور|چیپست|چیپ|sensor|chip/.test(t)) parts.push('سنسور')
  if (/هولدر|holder/.test(t)) parts.push('هولدر')
  if (/پکیج|ست کامل|package|kit/.test(t)) parts.push('پکیج')
  if (/دام|dome/.test(t)) parts.push('دام')
  const brands = []
  if (/سونی|sony/.test(t)) brands.push('سونی')
  if (/ytotech|ytot|yt|یوتوت/.test(t)) brands.push('YTOT')
  if (/vatilon|واتیلون/.test(t)) brands.push('Vatilon')
  if (/فولهان|fullhan/.test(t)) brands.push('فولهان')
  const usage = []
  if (/فروشگاه|shop|store/.test(t)) usage.push('فروشگاه')
  if (/منزل|خانه|home/.test(t)) usage.push('منزل')
  if (/انبار|warehouse/.test(t)) usage.push('انبار')
  return { mp, parts, brands, usage, raw: q.trim() }
}

// ─── جستجوی محصولات + راهنمایی محلی (پاسخ فوری) ───────────────
async function askBot(q) {
  const a = analyze(q)
  const kw = a.raw
  let products = []
  try {
    // جستجوی هوشمند بک‌اند (با اصلاح غلط‌های تایپی فارسی)
    const d = await api
      .get('/catalog/products/search/', { params: { q: kw } })
      .then((r) => r.data)
    products = (d?.results || []).slice(0, 3)
  } catch {}

  const tips = []
  if (a.mp)
    tips.push(`برای سیستم ${faNum(a.mp)} مگاپیکسل، لنز و سنسوری با رزولوشن مساوی یا بالاتر بگیر تا از کیفیت کامل استفاده کنی.`)
  if (a.parts.includes('لنز'))
    tips.push('فوکال لنز تعیین‌کننده فاصله دیده — فضای باز فوکال بیشتر (۸ یا ۱۲ میلی‌متر)، فضای بسته فوکال کمتر.')
  if (a.parts.includes('برد'))
    tips.push('برد رو بر اساس نوع دوربین (IP یا آنالوگ)، تعداد کانال و رزولوشن موردنیازت انتخاب کن؛ بردهای IP برای ارتقای بعدی انعطاف بیشتری دارن.')
  if (a.parts.includes('سنسور'))
    tips.push('سنسورهای سونی Starvis برای نور کم و دید در شب بهترین عملکرد رو دارن.')
  if (a.parts.includes('دام'))
    tips.push('دوربین دام برای نصب سقفی و فضای داخلی عالیه — برای بیرون حتماً بدنه ضدآب (IP66) بگیر.')
  if (a.usage.includes('فروشگاه'))
    tips.push('برای فروشگاه ترکیب دام سقفی + بولت برای ورودی با رزولوشن حداقل ۵ مگاپیکسل پیشنهاد می‌شه.')
  if (a.usage.includes('انبار'))
    tips.push('برای انبار به‌خاطر فاصله زیاد، لنز فوکال بالا و دوربین با IR قوی لازمه.')
  if (!tips.length)
    tips.push('برای راهنمایی دقیق‌تر، نام قطعه (لنز، برد، سنسور...) یا برند و رزولوشن مدنظرت رو بگو. «راهنمای انتخاب قطعه» هم قدم‌به‌قدم کمکت می‌کنه.')

  return {
    head: products.length
      ? 'بر اساس سوالت، این موارد از کاتالوگ بیشترین تطابق رو دارن:'
      : 'محصول کاملاً منطبقی پیدا نکردم، ولی این راهنمایی کمکت می‌کنه:',
    tips,
    products,
  }
}

// ═══════════════════════════════════════════════════════════════
// SmartSearch — باکس یکپارچه «جستجوی قطعه + پرسش از ربات مشاور»
// ═══════════════════════════════════════════════════════════════
export default function SmartSearch() {
  const [q, setQ] = useState('')
  const [lastQuery, setLastQuery] = useState('')
  const [phase, setPhase] = useState('idle') // idle | typing | done
  const [answer, setAnswer] = useState(null)
  const [aiPending, setAiPending] = useState(false)

  const submit = async (e) => {
    e?.preventDefault()
    const query = q.trim()
    if (!query || phase === 'typing') return
    setLastQuery(query)
    setPhase('typing')
    setAnswer(null)
    setAiPending(true)

    // ۱) پاسخ فوری محلی: محصولات مرتبط + راهنمایی — بدون انتظار برای AI
    const local = await askBot(query)
    setAnswer({ ...local, kind: 'local' })
    setPhase('done')

    // ۲) پاسخ هوش مصنوعی (کندتر روی CPU) — وقتی رسید جایگزین/تکمیل می‌شود
    try {
      const ai = await api
        .post('/catalog/assistant/ask/', { question: query }, { timeout: 130000 })
        .then((r) => r.data)
      if (ai?.answer && ai.source === 'ai') {
        setAnswer({ kind: 'ai', text: ai.answer, products: local.products })
      }
    } catch {}
    setAiPending(false)
  }

  return (
    <div
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: '1px solid var(--color-border-strong)',
        borderRadius: 22,
        boxShadow: 'var(--shadow-card-hover), 0 0 60px rgba(251,192,45,0.06)',
        padding: 'clamp(14px, 2.5vw, 22px)',
      }}
    >
      {/* فرم ورودی یکپارچه */}
      <form onSubmit={submit} style={{ display: 'flex', gap: 8 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Sparkles size={18} style={{ position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-brand)', pointerEvents: 'none' }} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="جستجوی قطعه یا پرسش از ربات مشاور... (مثل: لنز YTOT ۵ مگاپیکسل یا کدام برد برای دام مناسبه؟)"
            style={{
              width: '100%', height: 52, borderRadius: 14,
              border: '1px solid var(--color-border)',
              background: 'var(--color-bg-elevated)',
              color: 'var(--color-text-primary)',
              padding: '0 44px 0 16px', fontSize: 16, outline: 'none',
              transition: 'border-color 0.2s, box-shadow 0.2s',
            }}
            onFocus={(e) => { e.target.style.borderColor = 'var(--color-brand)'; e.target.style.boxShadow = '0 0 0 3px var(--color-brand-soft)' }}
            onBlur={(e) => { e.target.style.borderColor = 'var(--color-border)'; e.target.style.boxShadow = 'none' }}
          />
        </div>
        <button
          type="submit"
          disabled={!q.trim() || phase === 'typing'}
          className="btn-gold"
          style={{ height: 52, padding: '0 clamp(16px, 3vw, 26px)', borderRadius: 14, fontSize: 'clamp(13px, 2vw, 14px)', flexShrink: 0 }}
        >
          {phase === 'typing' ? <Loader2 size={17} className="animate-spin" /> : <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Search size={15} /> جستجو</span>}
        </button>
      </form>

      {/* چیپ‌های پیشنهادی */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
        {CHIPS.map((c) => (
          <button
            key={c}
            onClick={() => { setQ(c); }}
            style={{
              fontSize: 11, color: 'var(--color-text-secondary)',
              background: 'var(--color-brand-softer)',
              border: '1px solid var(--color-border)',
              borderRadius: 100, padding: '5px 13px', cursor: 'pointer', transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-brand)'; e.currentTarget.style.color = 'var(--color-brand)' }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; e.currentTarget.style.color = 'var(--color-text-secondary)' }}
          >
            {c}
          </button>
        ))}
      </div>

      {/* در حال جستجو */}
      {phase === 'typing' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 16, padding: '14px 16px', borderRadius: 14, background: 'var(--color-brand-softer)', border: '1px solid var(--color-border)' }}>
          <Bot size={17} color="var(--color-brand)" />
          <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>در حال جستجو و بررسی سوالت...</span>
        </div>
      )}

      {/* ناحیه پاسخ */}
      {phase === 'done' && answer && (
        <div className="animate-fade-in" style={{ marginTop: 16, padding: '16px', borderRadius: 14, background: 'var(--color-brand-softer)', border: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'var(--gradient-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Bot size={14} color="var(--color-brand-contrast)" />
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {answer.kind === 'ai' ? 'پاسخ هوش مصنوعی:' : answer.head}
            </span>
            {answer.kind === 'ai' && (
              <span style={{ fontSize: 9, fontWeight: 700, color: 'var(--color-brand)', background: 'var(--color-brand-soft)', border: '1px solid var(--color-border-strong)', borderRadius: 100, padding: '2px 8px', letterSpacing: 1 }}>AI</span>
            )}
          </div>

          {answer.kind === 'ai' && (
            <div style={{ fontSize: 13, color: 'var(--color-text-primary)', lineHeight: 1.9, paddingRight: 34 }}>{answer.text}</div>
          )}

          {answer.kind === 'local' && answer.tips.map((t, i) => (
            <div key={i} style={{ fontSize: 12.5, color: 'var(--color-text-secondary)', lineHeight: 1.8, paddingRight: 34, marginBottom: 4 }}>
              • {t}
            </div>
          ))}

          {/* منتظر پاسخ AI */}
          {answer.kind === 'local' && aiPending && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, paddingRight: 34 }}>
              <Loader2 size={13} className="animate-spin" color="var(--color-brand)" />
              <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>ربات مشاور هم داره روی سوالت فکر می‌کنه...</span>
            </div>
          )}

          {answer.products?.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(200px, 100%), 1fr))', gap: 8, marginTop: 12 }}>
              {answer.products.map((p) => {
                const img = mediaUrl(p.main_image?.image || p.images?.[0]?.image || p.image)
                // min_price سریالایزر لیست بر اساس سطح همکاری کاربر محاسبه می‌شود (ریال)
                // — مثل بقیه بخش‌های سایت. final_price واریانت (نقدی) نباید جایگزین شود.
                const price = p.min_price
                return (
                  <Link key={p.id} to={`/products/${p.slug || p.id}`} style={{ textDecoration: 'none' }}>
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: 10,
                      background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                      borderRadius: 12, transition: 'border-color 0.2s',
                    }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--color-brand)')}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
                    >
                      {img ? (
                        <img src={img} alt={p.name} style={{ width: 40, height: 40, objectFit: 'contain', borderRadius: 8, background: 'var(--color-bg-tertiary)' }} />
                      ) : (
                        <div style={{ width: 40, height: 40, borderRadius: 8, background: 'var(--color-bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)' }}>
                          <Camera size={18} />
                        </div>
                      )}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.7, overflowWrap: 'break-word' }}>{p.name}</div>
                        {price && <div style={{ fontSize: 11, color: 'var(--color-brand)', marginTop: 2 }}>{faNum(price)} ریال</div>}
                      </div>
                      <ArrowLeft size={13} color="var(--color-brand)" style={{ flexShrink: 0 }} />
                    </div>
                  </Link>
                )
              })}
            </div>
          )}

          {/* لینک همه نتایج جستجو */}
          <div style={{ marginTop: 12, paddingRight: 34 }}>
            <Link
              to={`/products?search=${encodeURIComponent(lastQuery)}`}
              style={{ fontSize: 12, color: 'var(--color-brand)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              مشاهده همه نتایج جستجو برای «{lastQuery}»
              <ArrowLeft size={12} />
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
