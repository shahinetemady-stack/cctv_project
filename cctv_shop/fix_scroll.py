import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ScrollToTop را به Layout.jsx اضافه می‌کنیم
layout_path = os.path.join(FRONTEND, 'components', 'layout', 'Layout.jsx')
with open(layout_path, encoding='utf-8') as f:
    layout = f.read()

if 'ScrollToTop' not in layout:
    # اضافه کردن import
    layout = layout.replace(
        "import { Outlet, Link, useLocation } from 'react-router-dom'",
        "import { Outlet, Link, useLocation, useEffect } from 'react-router-dom'"
    )

    # اضافه کردن ScrollToTop hook داخل Layout function
    old_layout_fn = """export default function Layout() {
  const { init } = useThemeStore()
  const { user } = useAuthStore()
  const location = useLocation()

  useEffect(() => init(), [])"""

    new_layout_fn = """export default function Layout() {
  const { init } = useThemeStore()
  const { user } = useAuthStore()
  const location = useLocation()

  useEffect(() => init(), [])

  // scroll to top on route change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [location.pathname])"""

    layout = layout.replace(old_layout_fn, new_layout_fn)
    print("✓ ScrollToTop به Layout اضافه شد")
else:
    print("✓ قبلاً موجود بود")

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(layout)
print("done")
