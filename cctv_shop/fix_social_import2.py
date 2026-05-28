import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
header_path = os.path.join(FRONTEND, 'components', 'layout', 'Header.jsx')

with open(header_path, encoding='utf-8') as f:
    content = f.read()

# درست کردن مسیر - از layout به components یک سطح بالاتر است
content = content.replace(
    "import { useSiteSettings } from '../../components/SocialButtons'",
    "import { useSiteSettings } from '../SocialButtons'"
)

with open(header_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ مسیر import درست شد")
print("مسیر صحیح: ../SocialButtons")
