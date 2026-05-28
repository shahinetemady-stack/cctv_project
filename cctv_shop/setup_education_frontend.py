import os, shutil

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
pages = os.path.join(FRONTEND, 'pages')

# ─── BlogPage ────────────────────────────────────────────────
with open(os.path.join(pages, 'BlogPage.jsx'), 'w', encoding='utf-8') as f:
    f.write("""import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'

function imgUrl(url) {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}

export default function BlogPage() {
  const { categorySlug } = useParams()
  const [search, setSearch] = useState('')

  const { data: articles = [] } = useQuery({
    queryKey: ['articles', categorySlug],
    queryFn: () => api.get('/education/articles/', {
      params: categorySlug ? { category: categorySlug } : {}
    }).then(r => r.data),
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['article-categories'],
    queryFn: () => api.get('/education/categories/').then(r => r.data),
  })

  const filtered = articles.filter(a =>
    !search || a.title.includes(search) || a.description.includes(search)
  )

  return (
    <div className="container-main py-12">
      <div className="text-center mb-10">
        <h1 className="font-display font-bold text-3xl text-white mb-3">📚 مقالات تخصصی</h1>
        <p className="text-gray-steel">راهنماها و مقالات تخصصی دوربین مداربسته</p>
      </div>

      <div className="flex gap-8">
        {/* سایدبار */}
        <div className="w-48 flex-shrink-0">
          <div className="card p-4 mb-4">
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="جستجو..." className="input text-sm w-full" />
          </div>
          <div className="card p-4">
            <h3 className="text-xs font-semibold text-white mb-3">دسته‌بندی‌ها</h3>
            <div className="space-y-1">
              <Link to="/blog" className={`block text-xs px-2 py-1.5 rounded ${!categorySlug ? 'text-brand bg-brand/10' : 'text-gray-steel hover:text-white'}`}>
                همه مقالات
              </Link>
              {categories.map(c => (
                <Link key={c.id} to={`/blog/category/${c.slug}`}
                  className={`block text-xs px-2 py-1.5 rounded ${categorySlug === c.slug ? 'text-brand bg-brand/10' : 'text-gray-steel hover:text-white'}`}>
                  {c.name}
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* مقالات */}
        <div className="flex-1">
          {filtered.length === 0 ? (
            <div className="text-center py-20 text-gray-steel">مقاله‌ای یافت نشد</div>
          ) : (
            <div className="grid grid-cols-2 gap-6">
              {filtered.map(a => (
                <Link key={a.id} to={`/blog/${a.slug}`}
                  className="card p-5 hover:border-brand/30 transition-all group">
                  {a.thumbnail && (
                    <img src={imgUrl(a.thumbnail)} alt={a.title}
                      className="w-full h-40 object-cover rounded-xl mb-4" />
                  )}
                  <div className="flex items-center gap-2 mb-2">
                    {a.category && (
                      <span className="text-[10px] bg-brand/20 text-brand px-2 py-0.5 rounded-full">
                        {a.category}
                      </span>
                    )}
                    <span className="text-[10px] text-gray-steel">{a.created_at}</span>
                  </div>
                  <h2 className="font-bold text-white text-sm mb-2 group-hover:text-brand transition-colors line-clamp-2">
                    {a.title}
                  </h2>
                  <p className="text-xs text-gray-steel line-clamp-3">{a.description}</p>
                  <div className="flex items-center gap-3 mt-3 text-[10px] text-gray-steel">
                    <span>👁 {a.views_count}</span>
                    <span>❤️ {a.likes_count}</span>
                    {a.author && <span>✍️ {a.author}</span>}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
""")

# ─── ArticleDetailPage ───────────────────────────────────────
with open(os.path.join(pages, 'ArticleDetailPage.jsx'), 'w', encoding='utf-8') as f:
    f.write("""import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import api from '../services/api'

function imgUrl(url) {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}

export default function ArticleDetailPage() {
  const { slug } = useParams()
  const { data: article, isLoading } = useQuery({
    queryKey: ['article', slug],
    queryFn: () => api.get(`/education/articles/${slug}/`).then(r => r.data),
  })

  if (isLoading) return <div className="container-main py-20 text-center text-gray-steel">در حال بارگذاری...</div>
  if (!article) return <div className="container-main py-20 text-center text-gray-steel">مقاله یافت نشد</div>

  return (
    <div className="container-main py-12 max-w-4xl">
      <Link to="/blog" className="text-sm text-gray-steel hover:text-white mb-6 block">← بازگشت به مقالات</Link>

      {article.thumbnail && (
        <img src={imgUrl(article.thumbnail)} alt={article.title}
          className="w-full h-64 object-cover rounded-2xl mb-8" />
      )}

      <div className="flex items-center gap-3 mb-4">
        {article.category && (
          <Link to={`/blog/category/${article.category_slug}`}
            className="text-xs bg-brand/20 text-brand px-3 py-1 rounded-full">
            {article.category}
          </Link>
        )}
        <span className="text-xs text-gray-steel">{article.created_at}</span>
        {article.author && <span className="text-xs text-gray-steel">✍️ {article.author}</span>}
      </div>

      <h1 className="font-display font-bold text-3xl text-white mb-6">{article.title}</h1>

      {/* محتوا */}
      <div className="card p-8 prose prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: article.content || `<p>${article.description}</p>` }} />

      {/* تگ‌ها */}
      {article.tags?.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-6">
          {article.tags.map(tag => (
            <span key={tag} className="text-xs bg-white/5 text-gray-steel px-3 py-1 rounded-full">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* محصولات مرتبط */}
      {article.related_products?.length > 0 && (
        <div className="mt-8">
          <h3 className="font-semibold text-white mb-4">محصولات مرتبط</h3>
          <div className="flex flex-wrap gap-3">
            {article.related_products.map(p => (
              <Link key={p.id} to={`/products/${p.slug}`}
                className="text-sm text-brand border border-brand/20 px-4 py-2 rounded-xl hover:bg-brand/10">
                {p.name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
""")

# ─── VideosPage ──────────────────────────────────────────────
with open(os.path.join(pages, 'VideosPage.jsx'), 'w', encoding='utf-8') as f:
    f.write("""import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'

function imgUrl(url) {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}

const VIDEO_TYPES = [
  { value: '', label: 'همه' },
  { value: 'montaj', label: 'نصب و راه‌اندازی' },
  { value: 'troubleshooting', label: 'عیب‌یابی' },
  { value: 'part_selection', label: 'انتخاب قطعه' },
  { value: 'general', label: 'عمومی' },
]

export default function VideosPage() {
  const [type, setType] = useState('')

  const { data: videos = [] } = useQuery({
    queryKey: ['videos', type],
    queryFn: () => api.get('/education/videos/', { params: type ? { type } : {} }).then(r => r.data),
  })

  return (
    <div className="container-main py-12">
      <div className="text-center mb-10">
        <h1 className="font-display font-bold text-3xl text-white mb-3">🎬 ویدیوهای آموزشی</h1>
        <p className="text-gray-steel">آموزش نصب، عیب‌یابی و انتخاب قطعه دوربین مداربسته</p>
      </div>

      <div className="flex gap-2 mb-8 flex-wrap">
        {VIDEO_TYPES.map(t => (
          <button key={t.value} onClick={() => setType(t.value)}
            className={`text-sm px-4 py-2 rounded-xl border transition-all ${
              type === t.value ? 'border-brand bg-brand/20 text-brand' : 'border-white/10 text-gray-steel hover:text-white'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {videos.length === 0 ? (
        <div className="text-center py-20 text-gray-steel">ویدیویی یافت نشد</div>
      ) : (
        <div className="grid grid-cols-3 gap-6">
          {videos.map(v => (
            <Link key={v.id} to={`/videos/${v.slug}`}
              className="card hover:border-brand/30 transition-all group overflow-hidden">
              {v.thumbnail ? (
                <img src={imgUrl(v.thumbnail)} alt={v.title}
                  className="w-full h-40 object-cover" />
              ) : (
                <div className="w-full h-40 bg-navy flex items-center justify-center">
                  <span className="text-4xl">▶️</span>
                </div>
              )}
              <div className="p-4">
                <span className="text-[10px] bg-brand/20 text-brand px-2 py-0.5 rounded-full">
                  {v.video_type_display}
                </span>
                <h3 className="font-semibold text-white text-sm mt-2 mb-1 group-hover:text-brand transition-colors line-clamp-2">
                  {v.title}
                </h3>
                <div className="flex items-center gap-3 text-[10px] text-gray-steel">
                  <span>⏱ {v.duration} دقیقه</span>
                  <span>👁 {v.views_count}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
""")

# ─── VideoDetailPage ─────────────────────────────────────────
with open(os.path.join(pages, 'VideoDetailPage.jsx'), 'w', encoding='utf-8') as f:
    f.write("""import { useQuery, useMutation } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { useEffect } from 'react'
import api from '../services/api'

export default function VideoDetailPage() {
  const { slug } = useParams()
  const { data: video, isLoading } = useQuery({
    queryKey: ['video', slug],
    queryFn: () => api.get(`/education/videos/${slug}/`).then(r => r.data),
  })

  useEffect(() => {
    if (slug) {
      api.post(`/education/videos/${slug}/view/`).catch(() => {})
    }
  }, [slug])

  if (isLoading) return <div className="container-main py-20 text-center text-gray-steel">در حال بارگذاری...</div>
  if (!video) return <div className="container-main py-20 text-center text-gray-steel">ویدیو یافت نشد</div>

  return (
    <div className="container-main py-12 max-w-4xl">
      <Link to="/videos" className="text-sm text-gray-steel hover:text-white mb-6 block">← بازگشت به ویدیوها</Link>

      <span className="text-xs bg-brand/20 text-brand px-3 py-1 rounded-full mb-4 inline-block">
        {video.video_type_display}
      </span>
      <h1 className="font-display font-bold text-2xl text-white mb-6">{video.title}</h1>

      {/* پلیر */}
      <div className="card overflow-hidden mb-6" style={{paddingBottom: '56.25%', position: 'relative', height: 0}}>
        <iframe
          src={video.embed_url}
          title={video.title}
          style={{position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none'}}
          allowFullScreen
        />
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-steel mb-6">
        <span>⏱ {video.duration} دقیقه</span>
        <span>👁 {video.views_count} بازدید</span>
      </div>

      {video.description && (
        <div className="card p-6 mb-6">
          <h2 className="font-semibold text-white mb-3">توضیحات</h2>
          <p className="text-sm text-gray-steel leading-relaxed">{video.description}</p>
        </div>
      )}

      {video.related_products?.length > 0 && (
        <div>
          <h3 className="font-semibold text-white mb-4">محصولات مرتبط</h3>
          <div className="flex flex-wrap gap-3">
            {video.related_products.map(p => (
              <Link key={p.id} to={`/products/${p.slug}`}
                className="text-sm text-brand border border-brand/20 px-4 py-2 rounded-xl hover:bg-brand/10">
                {p.name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
""")

# ─── PartSelectionGuidePage ──────────────────────────────────
with open(os.path.join(pages, 'PartSelectionGuidePage.jsx'), 'w', encoding='utf-8') as f:
    f.write("""import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'

export default function PartSelectionGuidePage() {
  const { data } = useQuery({
    queryKey: ['part-selection-guide'],
    queryFn: () => api.get('/education/guides/part-selection/').then(r => r.data),
  })

  return (
    <div className="container-main py-12 max-w-4xl">
      <div className="text-center mb-10">
        <h1 className="font-display font-bold text-3xl text-white mb-3">🎯 راهنمای انتخاب قطعه</h1>
        <p className="text-gray-steel">چطور قطعه مناسب دوربین مداربسته را انتخاب کنیم؟</p>
      </div>

      {/* اینفوگرافیک */}
      <div className="grid grid-cols-4 gap-4 mb-10">
        {[
          { icon: '📐', title: 'محل نصب', desc: 'داخلی یا خارجی؟ فاصله دید؟' },
          { icon: '💡', title: 'نور محیط', desc: 'روز/شب؟ نور مصنوعی؟' },
          { icon: '📺', title: 'کیفیت تصویر', desc: '2MP, 4MP یا 8MP؟' },
          { icon: '🔌', title: 'زیرساخت', desc: 'کابل موجود؟ برق؟' },
        ].map(item => (
          <div key={item.title} className="card p-4 text-center">
            <div className="text-3xl mb-2">{item.icon}</div>
            <div className="text-sm font-semibold text-white mb-1">{item.title}</div>
            <div className="text-xs text-gray-steel">{item.desc}</div>
          </div>
        ))}
      </div>

      {/* محتوای راهنما */}
      {data?.guide?.content ? (
        <div className="card p-8 mb-8"
          dangerouslySetInnerHTML={{ __html: data.guide.content }} />
      ) : (
        <div className="card p-8 mb-8">
          <h2 className="font-bold text-white text-xl mb-6">مراحل انتخاب قطعه مناسب</h2>
          <div className="space-y-6">
            {[
              { step: '۱', title: 'تعیین کاربرد', desc: 'آیا دوربین برای نظارت داخلی است یا خارجی؟ آیا شب هم باید تصویر بگیرد؟' },
              { step: '۲', title: 'انتخاب رزولوشن', desc: '2 مگاپیکسل برای فضاهای کوچک، 4MP برای متوسط و 8MP برای فضاهای بزرگ مناسب است.' },
              { step: '۳', title: 'انتخاب لنز', desc: 'فاصله دید مستقیم با focal length لنز رابطه دارد. برای فضاهای باز لنز با focal بیشتر مناسب است.' },
              { step: '۴', title: 'انتخاب برد', desc: 'برد باید با لنز و رزولوشن سازگار باشد. به ولتاژ ورودی توجه کنید.' },
              { step: '۵', title: 'محاسبه کابل‌کشی', desc: 'طول مسیر کابل را حساب کنید. برای مسافت‌های طولانی از کابل با سطح مقطع بیشتر استفاده کنید.' },
            ].map(item => (
              <div key={item.step} className="flex gap-4">
                <div className="w-10 h-10 bg-brand rounded-full flex items-center justify-center text-white font-bold flex-shrink-0">
                  {item.step}
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                  <p className="text-sm text-gray-steel">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ویدیوهای مرتبط */}
      {data?.videos?.length > 0 && (
        <div>
          <h2 className="font-bold text-white text-xl mb-4">🎬 ویدیوهای آموزشی</h2>
          <div className="grid grid-cols-2 gap-4">
            {data.videos.map(v => (
              <Link key={v.slug} to={`/videos/${v.slug}`}
                className="card p-4 hover:border-brand/30 transition-all flex items-center gap-3">
                <div className="w-12 h-12 bg-brand/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <span className="text-xl">▶️</span>
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{v.title}</div>
                  <div className="text-xs text-gray-steel">⏱ {v.duration} دقیقه</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
""")

print("✓ همه صفحات education ساخته شدند")

# ─── آپدیت App.jsx ───────────────────────────────────────────
app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'BlogPage' not in app:
    app = app.replace(
        "import ChinaOrderPage",
        """import BlogPage from './pages/BlogPage'
import ArticleDetailPage from './pages/ArticleDetailPage'
import VideosPage from './pages/VideosPage'
import VideoDetailPage from './pages/VideoDetailPage'
import PartSelectionGuidePage from './pages/PartSelectionGuidePage'
import ChinaOrderPage"""
    )
    app = app.replace(
        '<Route path="china-order"',
        """<Route path="blog" element={<BlogPage />} />
        <Route path="blog/category/:categorySlug" element={<BlogPage />} />
        <Route path="blog/:slug" element={<ArticleDetailPage />} />
        <Route path="videos" element={<VideosPage />} />
        <Route path="videos/:slug" element={<VideoDetailPage />} />
        <Route path="guides/part-selection" element={<PartSelectionGuidePage />} />
        <Route path="china-order" """
    )
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("✓ App.jsx آپدیت شد")

# اضافه کردن به Footer
footer_path = os.path.join(FRONTEND, 'components', 'layout', 'Footer.jsx')
with open(footer_path, encoding='utf-8') as f:
    footer = f.read()

if '/blog' not in footer:
    footer = footer.replace(
        "['🇨🇳 سفارش از چین', '/china-order'],",
        "['📚 مقالات', '/blog'],\n                ['🎬 ویدیوها', '/videos'],\n                ['🎯 راهنمای انتخاب', '/guides/part-selection'],\n                ['🇨🇳 سفارش از چین', '/china-order'],"
    )
    with open(footer_path, 'w', encoding='utf-8') as f:
        f.write(footer)
    print("✓ لینک‌های آموزش به Footer اضافه شد")

print("\nآدرس‌های جدید:")
print("  /blog — مقالات")
print("  /videos — ویدیوها")
print("  /guides/part-selection — راهنمای انتخاب قطعه")
print("\nمدیریت در Django Admin:")
print("  http://127.0.0.1:8000/admin/education/")
