import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
layout_path = os.path.join(FRONTEND, 'components', 'layout', 'Layout.jsx')

with open(layout_path, encoding='utf-8') as f:
    content = f.read()

# حذف import useEffect از react (تکراری)
content = content.replace(
    "import { useEffect } from 'react'\n",
    ""
)

# اطمینان از اینکه useEffect از react-router-dom حذف شود
# و فقط از react بیاید
content = content.replace(
    "import { Outlet, Link, useLocation, useEffect } from 'react-router-dom'",
    "import { Outlet, Link, useLocation } from 'react-router-dom'"
)

# اضافه کردن useEffect از react
if "import { useEffect } from 'react'" not in content and "import { useQuery" in content:
    content = content.replace(
        "import { useQuery }",
        "import { useEffect as useEffectReact } from 'react'\nimport { useQuery }"
    )
    content = content.replace(
        "  useEffect(() => init(), [])",
        "  useEffectReact(() => init(), [])"
    )
    content = content.replace(
        "  // scroll to top on route change\n  useEffect(() => {",
        "  // scroll to top on route change\n  useEffectReact(() => {"
    )
elif "import { useQuery" in content:
    content = content.replace(
        "import { useQuery }",
        "import { useEffect } from 'react'\nimport { useQuery }"
    )

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)

# تأیید
lines = content.split('\n')
print("=== ۵ خط اول ===")
for i, l in enumerate(lines[:5], 1):
    print(f"{i}: {l}")
print("useEffect count:", content.count('useEffect'))
