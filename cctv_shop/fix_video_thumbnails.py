import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

def fix_video_thumbnail(content):
    """جایگزینی تابع نمایش ویدیو برای دریافت thumbnail خودکار از یوتیوب/آپارات"""

    # اضافه کردن تابع getVideoThumbnail
    thumbnail_fn = """
function getVideoThumbnail(video) {
  if (video.thumbnail) {
    const url = video.thumbnail
    if (url.startsWith('http')) return url
    return `http://localhost:8000${url}`
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

"""
    return thumbnail_fn, content

# ─── Fix VideosPage ───────────────────────────────────────────
videos_path = os.path.join(FRONTEND, 'pages', 'VideosPage.jsx')
with open(videos_path, encoding='utf-8') as f:
    content = f.read()

if 'getVideoThumbnail' not in content:
    thumbnail_fn, _ = fix_video_thumbnail(content)
    content = content.replace(
        "const VIDEO_TYPES",
        thumbnail_fn + "const VIDEO_TYPES"
    )
    # جایگزینی نمایش thumbnail در کارت ویدیو
    content = content.replace(
        """              <img src={imgUrl(v.thumbnail)} alt={v.title}
                  className="w-full h-40 object-cover" />
              ) : (
                <div className="w-full h-40 bg-navy flex items-center justify-center">
                  <span className="text-4xl">▶️</span>
                </div>""",
        """              <img src={getVideoThumbnail(v)} alt={v.title}
                  className="w-full h-40 object-cover" />
              ) : (
                <div className="w-full h-40 bg-navy flex items-center justify-center">
                  <span className="text-4xl">▶️</span>
                </div>"""
    )
    content = content.replace(
        "{v.thumbnail ? (",
        "{getVideoThumbnail(v) ? ("
    )
    with open(videos_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ VideosPage.jsx آپدیت شد")

# ─── Fix HomePage FeaturedVideos ─────────────────────────────
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')
with open(home_path, encoding='utf-8') as f:
    content = f.read()

if 'getVideoThumbnail' not in content:
    thumbnail_fn, _ = fix_video_thumbnail(content)
    content = content.replace(
        "// ─── ویدیوهای آموزشی",
        thumbnail_fn + "// ─── ویدیوهای آموزشی"
    )
    # جایگزینی در کارت ویدیو
    old = """            {v.thumbnail ? (
              <img src={imgUrl(v.thumbnail)} alt={v.title} className="w-full h-36 object-cover" />
            ) : (
              <div className="w-full h-36 bg-gradient-to-br from-navy to-steel flex items-center justify-center">
                <span className="text-5xl">▶️</span>
              </div>
            )}"""
    new = """            {getVideoThumbnail(v) ? (
              <img src={getVideoThumbnail(v)} alt={v.title} className="w-full h-36 object-cover" />
            ) : (
              <div className="w-full h-36 bg-gradient-to-br from-navy to-steel flex items-center justify-center">
                <span className="text-5xl">▶️</span>
              </div>
            )}"""
    content = content.replace(old, new)
    with open(home_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ HomePage FeaturedVideos آپدیت شد")

# ─── Fix VideoDetailPage ──────────────────────────────────────
detail_path = os.path.join(FRONTEND, 'pages', 'VideoDetailPage.jsx')
with open(detail_path, encoding='utf-8') as f:
    content = f.read()
print("✓ done")
