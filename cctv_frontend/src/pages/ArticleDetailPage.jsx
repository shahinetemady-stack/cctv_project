import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import Seo, { absoluteUrl } from '../components/Seo'
import { mediaUrl as imgUrl } from '../utils/media'
import { formatDate } from '../utils/date'

export default function ArticleDetailPage() {
  const { slug } = useParams()
  const { data: article, isLoading } = useQuery({
    queryKey: ['article', slug],
    queryFn: () => api.get(`/education/articles/${slug}/`).then(r => r.data),
  })

  // اگر API به‌خاطر اسلاگ قدیمی ۳۰۱ شده، آدرس مرورگر را با اسلاگ جدید جایگزین کن
  const navigate = useNavigate()
  useEffect(() => {
    if (article?.slug && article.slug !== slug) {
      navigate(`/blog/${article.slug}`, { replace: true })
    }
  }, [article?.slug, slug])

  if (isLoading) return <div className="container-main py-20 text-center text-gray-steel">در حال بارگذاری...</div>
  if (!article) return <div className="container-main py-20 text-center text-gray-steel">مقاله یافت نشد</div>

  // ─── SEO/GEO ─────────────────────────────────────────────────
  const canonical = `/blog/${article.slug}`
  const articleLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: article.title,
    ...(article.author && { author: { '@type': 'Person', name: article.author } }),
    ...(article.created_at && { datePublished: article.created_at }),
    ...(article.updated_at && { dateModified: article.updated_at }),
    ...(article.thumbnail && { image: absoluteUrl(imgUrl(article.thumbnail)) }),
  }

  return (
    <div className="container-main py-12 max-w-4xl">
      <Seo
        title={`${article.title} | دوربینکار`}
        description={article.description}
        keywords={article.tags}
        canonical={canonical}
        image={imgUrl(article.thumbnail)}
        jsonLd={articleLd}
      />
      <Link to="/blog" className="text-sm text-gray-steel hover:text-white mb-6 block">← بازگشت به مقالات</Link>

      {article.thumbnail && (
        <img src={imgUrl(article.thumbnail)} alt={article.title}
          className="w-full aspect-video object-cover rounded-2xl mb-8" />
      )}

      <div className="flex items-center gap-3 mb-4">
        {article.category && (
          <Link to={`/blog/category/${article.category_slug}`}
            className="text-xs bg-brand/20 text-brand px-3 py-1 rounded-full">
            {article.category}
          </Link>
        )}
        <span className="text-xs text-gray-steel">{formatDate(article.created_at)}</span>
        {article.author && <span className="text-xs text-gray-steel">✍️ {article.author}</span>}
      </div>

      <h1 className="font-display font-bold text-3xl text-white mb-6">{article.title}</h1>

      {/* محتوا */}
      <div className="card p-8 article-content"
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
