import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── 1. حذف تکراری از HomePage ───────────────────────────────
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')
with open(home_path, encoding='utf-8') as f:
    content = f.read()

# شمارش تعداد FeaturedPackages
count = content.count('<FeaturedPackages')
print(f"FeaturedPackages count: {count}")

if count > 1:
    # حذف اولین import تکراری
    import_count = content.count("import { FeaturedPackages }")
    print(f"import count: {import_count}")
    if import_count > 1:
        content = content.replace(
            "import { FeaturedPackages } from '../components/PackageComponents'\n",
            "", 1
        )
    # حذف اولین <FeaturedPackages />
    first_idx = content.find('<FeaturedPackages')
    second_idx = content.find('<FeaturedPackages', first_idx + 1)
    if second_idx > 0:
        # حذف اولی با newline
        content = content[:first_idx] + content[content.find('\n', first_idx)+1:]
    print("✓ تکراری حذف شد")

with open(home_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"New count: {content.count('<FeaturedPackages')}")

# ─── 2. اصلاح عکس در PackageDetailPage ──────────────────────
detail_path = os.path.join(FRONTEND, 'pages', 'PackageDetailPage.jsx')
with open(detail_path, encoding='utf-8') as f:
    detail = f.read()

# اضافه کردن imgUrl
if 'imgUrl' not in detail:
    old = "function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }"
    new = """function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function imgUrl(url) {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}"""
    detail = detail.replace(old, new)
    print("✓ imgUrl اضافه شد")

# جایگزینی src های عکس
detail = detail.replace('src={item.image}', 'src={imgUrl(item.image)}')
detail = detail.replace('src={pkg.image}', 'src={imgUrl(pkg.image)}')

# اضافه کردن عکس پکیج در صفحه جزئیات اگر نبود
if 'pkg.image &&' not in detail:
    old_h1 = '      <h1 className="font-display font-bold text-2xl text-white mb-2">{pkg.name}</h1>'
    new_h1 = '''      {pkg.image && (
        <img src={imgUrl(pkg.image)} alt={pkg.name}
          className="w-full h-56 object-cover rounded-2xl mb-6 bg-white/5" />
      )}
      <h1 className="font-display font-bold text-2xl text-white mb-2">{pkg.name}</h1>'''
    detail = detail.replace(old_h1, new_h1)
    print("✓ عکس به صفحه جزئیات اضافه شد")

with open(detail_path, 'w', encoding='utf-8') as f:
    f.write(detail)
print("done")
