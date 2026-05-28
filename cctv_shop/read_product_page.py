import os, shutil

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

print("Lines:", content.count('\n'))
print("Has stock check:", 'stock' in content.lower())
print("Has out_of_stock:", 'out_of_stock' in content)
print("Has final_price:", 'final_price' in content)

# نمایش آخر فایل
lines = content.split('\n')
print("\n=== آخر فایل ===")
for i, line in enumerate(lines[-30:], len(lines)-30):
    print(f"{i}: {line}")
