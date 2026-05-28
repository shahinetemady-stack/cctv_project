import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# نمایش ۱۰ خط اول و ۱۰ خط آخر
lines = content.split('\n')
print("=== ۱۰ خط اول ===")
for i, l in enumerate(lines[:10], 1):
    print(f"{i}: {l}")

print("\n=== محل SimilarProducts ===")
for i, l in enumerate(lines, 1):
    if 'SimilarProducts' in l or 'export default' in l:
        print(f"{i}: {l}")
