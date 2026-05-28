import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
header_path = os.path.join(FRONTEND, 'components', 'layout', 'Header.jsx')

with open(header_path, encoding='utf-8') as f:
    content = f.read()

# حذف import SocialButtons و جایگزینی با useQuery مستقیم
content = content.replace(
    "import { useSiteSettings } from '../SocialButtons'\n",
    ""
)
content = content.replace(
    "import { useSiteSettings } from '../../components/SocialButtons'\n",
    ""
)

# اضافه کردن useQuery و api import اگر نبود
if 'useQuery' not in content:
    content = content.replace(
        "import { useState,",
        "import { useQuery } from '@tanstack/react-query'\nimport api from '../../services/api'\nimport { useState,"
    )

# تغییر useSiteSettings به useQuery مستقیم
content = content.replace(
    "  const { data: settings } = useSiteSettings()",
    """  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then(r => r.data),
    staleTime: 300000,
  })"""
)

with open(header_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ Header.jsx درست شد")
