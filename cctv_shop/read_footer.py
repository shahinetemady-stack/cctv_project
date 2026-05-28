import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
footer_path = os.path.join(FRONTEND, 'components', 'layout', 'Footer.jsx')

with open(footer_path, encoding='utf-8') as f:
    content = f.read()

print(content)
