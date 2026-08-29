import { Helmet } from 'react-helmet-async'

// ─── SEO/GEO ───────────────────────────────────────────────────
// مدیریت متمرکز <head> برای صفحات عمومی: title، meta، Open Graph،
// canonical، متاهای جغرافیایی و JSON-LD (schema.org).
const SITE_URL = (import.meta.env.VITE_SITE_URL || 'https://doorbinkar.com').replace(/\/+$/, '')

/** تبدیل مسیر نسبی به URL کامل با دامنه سایت */
export function absoluteUrl(url) {
  if (!url) return null
  if (/^https?:\/\//i.test(url)) return url
  return `${SITE_URL}${url.startsWith('/') ? url : `/${url}`}`
}

export default function Seo({
  title,
  description,
  keywords,
  canonical,
  image,
  geoTags = [],
  jsonLd,
}) {
  const canonicalUrl = absoluteUrl(canonical)
  const imageUrl = absoluteUrl(image)
  // geoTags ممکن است رشته‌ی جداشده با ویرگول یا آرایه باشد
  const places = Array.isArray(geoTags)
    ? geoTags
    : String(geoTags || '').split(/[،,]/).map(s => s.trim()).filter(Boolean)
  const jsonLds = jsonLd ? (Array.isArray(jsonLd) ? jsonLd : [jsonLd]) : []

  return (
    <Helmet>
      {title && <title>{title}</title>}
      {description && <meta name="description" content={description} />}
      {keywords && <meta name="keywords" content={Array.isArray(keywords) ? keywords.join(', ') : keywords} />}

      {/* Open Graph */}
      {title && <meta property="og:title" content={title} />}
      {description && <meta property="og:description" content={description} />}
      {imageUrl && <meta property="og:image" content={imageUrl} />}
      {canonicalUrl && <meta property="og:url" content={canonicalUrl} />}
      <meta property="og:type" content="website" />
      <meta property="og:locale" content="fa_IR" />

      {/* Twitter Card */}
      <meta name="twitter:card" content={imageUrl ? 'summary_large_image' : 'summary'} />
      {title && <meta name="twitter:title" content={title} />}
      {description && <meta name="twitter:description" content={description} />}
      {imageUrl && <meta name="twitter:image" content={imageUrl} />}

      {/* Canonical */}
      {canonicalUrl && <link rel="canonical" href={canonicalUrl} />}

      {/* متا‌های جغرافیایی */}
      <meta name="geo.region" content="IR" />
      {places.length > 0 && <meta name="geo.placename" content={places.join(', ')} />}

      {/* داده ساخت‌یافته JSON-LD */}
      {jsonLds.map((schema, i) => (
        <script key={i} type="application/ld+json">
          {JSON.stringify(schema)}
        </script>
      ))}
    </Helmet>
  )
}
