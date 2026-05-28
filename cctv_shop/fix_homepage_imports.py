import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')

with open(home_path, encoding='utf-8') as f:
    content = f.read()

# نمایش ۱۰ خط اول
lines = content.split('\n')
print("=== ۱۰ خط اول ===")
for i, l in enumerate(lines[:10], 1):
    print(f"{i}: {l}")

# حذف import تکراری
# اگر useQuery دو بار import شده
if content.count("from '@tanstack/react-query'") > 1:
    # حذف خط اضافه
    content = content.replace(
        "import { useQuery } from '@tanstack/react-query'\nimport api from '../services/api'\n\n  from '@tanstack/react-query'",
        "import { useQuery } from '@tanstack/react-query'\nimport api from '../services/api'"
    )
    # یا روش دیگر
    content = content.replace(
        "\n  from '@tanstack/react-query'\n",
        "\n"
    )
    print("✓ import تکراری حذف شد")

# پاک کردن هر خط که فقط "from" داشته باشد
new_lines = []
for line in content.split('\n'):
    stripped = line.strip()
    if stripped.startswith("from '") and not stripped.startswith("from 'react"):
        # این یک import ناقص است
        if not any(kw in line for kw in ['import', 'export']):
            print(f"حذف خط ناقص: {repr(line)}")
            continue
    new_lines.append(line)
content = '\n'.join(new_lines)

with open(home_path, 'w', encoding='utf-8') as f:
    f.write(content)

# نمایش ۱۰ خط اول بعد از اصلاح
lines = content.split('\n')
print("\n=== بعد از اصلاح ===")
for i, l in enumerate(lines[:10], 1):
    print(f"{i}: {l}")
