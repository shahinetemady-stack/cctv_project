import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
footer_path = os.path.join(FRONTEND, 'components', 'layout', 'Footer.jsx')

with open(footer_path, encoding='utf-8') as f:
    content = f.read()

# تغییر staleTime به 0 تا همیشه fresh باشد
content = content.replace(
    "staleTime: 300000,",
    "staleTime: 0,"
)

with open(footer_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ staleTime به 0 تغییر کرد")
print("صفحه را refresh کنید")
