// ─── نوار مارکی برندها — لوگوهای متنی با اسکرول بی‌نهایت ──────
const MONO = "'JetBrains Mono', monospace"

const BRANDS = [
  { name: 'VATILON',   style: { fontWeight: 800, letterSpacing: 3 } },
  { name: 'HS',        style: { fontFamily: MONO, fontWeight: 800, border: '2px solid currentColor', borderRadius: 6, padding: '1px 9px', letterSpacing: 1 } },
  { name: 'YTOT',      style: { fontStyle: 'italic', fontWeight: 800, letterSpacing: 0.5 } },
  { name: 'CW',        style: { fontFamily: MONO, fontWeight: 800, letterSpacing: 2 } },
  { name: 'RUISION',   style: { fontWeight: 700, letterSpacing: 4 } },
  { name: 'ANJVISION', style: { fontWeight: 800, letterSpacing: -0.5 } },
  { name: 'XM',        style: { fontFamily: MONO, fontWeight: 800, fontStyle: 'italic', letterSpacing: 1 } },
]

export default function BrandMarquee() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 'clamp(16px, 3vw, 40px)',
      background: 'var(--gradient-gold)',
      borderRadius: 'clamp(14px, 2vw, 20px)',
      padding: 'clamp(14px, 2.5vw, 22px) clamp(18px, 3vw, 32px)',
      boxShadow: '0 8px 40px rgba(251,192,45,0.25), inset 0 1px 0 rgba(255,255,255,0.25)',
      color: 'var(--color-brand-contrast)',
      overflow: 'hidden',
    }}>
      {/* لیبل ثابت */}
      <span style={{
        flexShrink: 0, fontFamily: MONO, fontWeight: 800,
        fontSize: 'clamp(10px, 1.6vw, 13px)', letterSpacing: 2, whiteSpace: 'nowrap',
      }}>
        BRANDS WE SUPPORT
      </span>

      {/* جداکننده */}
      <span style={{ flexShrink: 0, width: 2, alignSelf: 'stretch', background: 'rgba(0,0,0,0.18)', borderRadius: 2 }} />

      {/* ویوپورت مارکی */}
      <div className="marquee-viewport" dir="ltr">
        <div className="marquee-track">
          {[...BRANDS, ...BRANDS].map((b, i) => (
            <span key={i} style={{
              padding: '0 clamp(20px, 3vw, 36px)',
              fontSize: 'clamp(14px, 2.2vw, 19px)',
              whiteSpace: 'nowrap',
              fontFamily: "'Exo 2', Vazirmatn, sans-serif",
              ...b.style,
            }}>
              {b.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
