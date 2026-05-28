import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# بررسی محل SimilarProducts
idx = content.find('function SimilarProducts')
export_idx = content.find('export default function')
print(f"SimilarProducts at: {idx}")
print(f"export default at: {export_idx}")

if idx > export_idx and idx > 0:
    print("مشکل: SimilarProducts بعد از export default است — درست می‌کنیم")
    
    # استخراج کامپوننت SimilarProducts
    start = content.find('\n// ─── جایگزین')
    if start < 0:
        start = content.find('\nfunction SimilarProducts')
    end = content.find('\nexport default function', start)
    
    similar_block = content[start:end]
    
    # حذف از محل فعلی
    content = content[:start] + content[end:]
    
    # اضافه کردن قبل از export default
    content = content.replace('export default function', similar_block + '\nexport default function')
    
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # تأیید
    new_idx = content.find('function SimilarProducts')
    new_export = content.find('export default function')
    print(f"✓ SimilarProducts at: {new_idx}, export at: {new_export}")
    print("✓ درست شد" if new_idx < new_export else "✗ هنوز مشکل دارد")
else:
    print("ترتیب درست است")
