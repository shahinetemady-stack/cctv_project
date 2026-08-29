import { useQuery, useMutation } from '@tanstack/react-query'
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
