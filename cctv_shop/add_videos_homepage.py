import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')

with open(home_path, encoding='utf-8') as f:
    content = f.read()

# کامپوننت FeaturedVideos
featured_videos = """
// ─── ویدیوهای آموزشی ─────────────────────────────────────────
function FeaturedVideos() {
  const { data: videos = [] } = useQuery({
    queryKey: ['featured-videos'],
    queryFn: () => api.get('/education/videos/').then(r => r.data),
    staleTime: 300000,
  })

  if (!videos.length) return null

  function imgUrl(url) {
    if (!url) return null
    if (url.startsWith('http')) return url
    return `http://localhost:8000${url}`
  }

  return (
    <section className="py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display font-bold text-2xl text-white">🎬 ویدیوهای آموزشی</h2>
          <p className="text-sm text-gray-steel mt-1">آموزش نصب و راه‌اندازی دوربین مداربسته</p>
        </div>
        <Link to="/videos" className="text-sm text-brand hover:text-brand/80">همه ویدیوها ←</Link>
      </div>
      <div className="grid grid-cols-3 gap-5">
        {videos.slice(0, 3).map(v => (
          <Link key={v.id} to={`/videos/${v.slug}`}
            className="card hover:border-brand/30 transition-all group overflow-hidden">
            {v.thumbnail ? (
              <img src={imgUrl(v.thumbnail)} alt={v.title} className="w-full h-36 object-cover" />
            ) : (
              <div className="w-full h-36 bg-gradient-to-br from-navy to-steel flex items-center justify-center">
                <span className="text-5xl">▶️</span>
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
    </section>
  )
}

"""

if 'FeaturedVideos' not in content:
    content = content.replace(
        '// ─── مقالات برتر',
        featured_videos + '// ─── مقالات برتر'
    )
    print("✓ FeaturedVideos کامپوننت اضافه شد")

# اضافه کردن به JSX — قبل از مقالات
if '<FeaturedVideos' not in content:
    content = content.replace(
        '        <FeaturedArticles />',
        '        <FeaturedVideos />\n\n        <FeaturedArticles />'
    )
    print("✓ FeaturedVideos به HomePage اضافه شد")

with open(home_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
