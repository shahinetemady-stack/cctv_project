import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
comp_path = os.path.join(FRONTEND, 'components', 'PackageComponents.jsx')

with open(comp_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن عکس پکیج به کارت
old = '''      {/* هدر */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-bold text-white text-sm">{pkg.name}</h3>
          {pkg.description && (
            <p className="text-xs text-gray-steel mt-1 line-clamp-2">{pkg.description}</p>
          )}
        </div>
        <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded-full font-bold flex-shrink-0 mr-2">
          {pkg.discount_percent}% تخفیف
        </span>
      </div>'''

new = '''      {/* عکس پکیج */}
      {pkg.image && (
        <img src={imgUrl(pkg.image)} alt={pkg.name}
          className="w-full h-36 object-cover rounded-xl mb-4 bg-white/5" />
      )}

      {/* هدر */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-bold text-white text-sm">{pkg.name}</h3>
          {pkg.description && (
            <p className="text-xs text-gray-steel mt-1 line-clamp-2">{pkg.description}</p>
          )}
        </div>
        <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded-full font-bold flex-shrink-0 mr-2">
          {pkg.discount_percent}% تخفیف
        </span>
      </div>'''

if old in content:
    content = content.replace(old, new)
    print("✓ عکس پکیج اضافه شد")
else:
    print("✗ متن پیدا نشد")

with open(comp_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
