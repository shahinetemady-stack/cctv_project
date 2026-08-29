import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'
import { mediaUrl as imgUrl } from '../utils/media'


function getVideoThumbnail(video) {
  if (video.thumbnail) {
    return imgUrl(video.thumbnail)
  }
  // thumbnail خودکار از یوتیوب
  const url = video.video_url || video.embed_url || ''
  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    let vid = ''
    if (url.includes('embed/')) vid = url.split('embed/')[1].split('?')[0]
    else if (url.includes('watch?v=')) vid = url.split('watch?v=')[1].split('&')[0]
    else if (url.includes('youtu.be/')) vid = url.split('youtu.be/')[1].split('?')[0]
    if (vid) return `https://img.youtube.com/vi/${vid}/mqdefault.jpg`
  }
  return null
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {videos.map(v => (
            <Link key={v.id} to={`/videos/${v.slug}`}
              className="card hover:border-brand/30 transition-all group overflow-hidden">
              {getVideoThumbnail(v) ? (
                <img src={getVideoThumbnail(v)} alt={v.title}
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
