import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
header_path = os.path.join(FRONTEND, 'components', 'layout', 'Header.jsx')

with open(header_path, encoding='utf-8') as f:
    content = f.read()

# درست کردن مسیر import
content = content.replace(
    "import { useSiteSettings } from '../SocialButtons'",
    "import { useSiteSettings } from '../../components/SocialButtons'"
)

# اگر مسیر دیگری بود
content = content.replace(
    "from '../SocialButtons'",
    "from '../../components/SocialButtons'"
)

with open(header_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ مسیر import درست شد")
