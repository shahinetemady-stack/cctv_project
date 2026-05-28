import { useQuery } from '@tanstack/react-query'
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
