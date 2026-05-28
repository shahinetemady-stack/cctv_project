import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
comp_path = os.path.join(FRONTEND, 'components', 'PackageComponents.jsx')

with open(comp_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن helper برای URL عکس
old_fmt = "function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }"
new_fmt = """function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function imgUrl(url) {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `${import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000'}${url}`
}"""

content = content.replace(old_fmt, new_fmt)

# جایگزینی تمام src={item.image} و src={pkg.image}
content = content.replace('src={item.image}', 'src={imgUrl(item.image)}')
content = content.replace('src={pkg.image}', 'src={imgUrl(pkg.image)}')

with open(comp_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ PackageComponents.jsx اصلاح شد")

# اصلاح PackageDetailPage.jsx هم
detail_path = os.path.join(FRONTEND, 'pages', 'PackageDetailPage.jsx')
with open(detail_path, encoding='utf-8') as f:
    detail = f.read()

if 'imgUrl' not in detail:
    detail = detail.replace(
        "function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }",
        """function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function imgUrl(url) {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `${import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000'}${url}`
}"""
    )
    detail = detail.replace('src={item.image}', 'src={imgUrl(item.image)}')
    detail = detail.replace('src={pkg.image}', 'src={imgUrl(pkg.image)}')
    with open(detail_path, 'w', encoding='utf-8') as f:
        f.write(detail)
    print("✓ PackageDetailPage.jsx اصلاح شد")

print("done")
