import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── 1. ساخت ScrollToTop component ───────────────────────────
scroll_component = """import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export default function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [pathname])
  return null
}
"""

comp_path = os.path.join(FRONTEND, 'components', 'ScrollToTop.jsx')
with open(comp_path, 'w', encoding='utf-8') as f:
    f.write(scroll_component)
print("✓ ScrollToTop.jsx ساخته شد")

# ─── 2. اضافه کردن به App.jsx ─────────────────────────────────
app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'ScrollToTop' not in app:
    # اضافه کردن import
    app = app.replace(
        "import { BrowserRouter",
        "import ScrollToTop from './components/ScrollToTop'\nimport { BrowserRouter"
    )
    # اضافه کردن بعد از <BrowserRouter> یا <Router>
    # پیدا کردن محل مناسب — بعد از Router tag
    if '<BrowserRouter>' in app:
        app = app.replace('<BrowserRouter>', '<BrowserRouter>\n      <ScrollToTop />')
    elif '<Router>' in app:
        app = app.replace('<Router>', '<Router>\n      <ScrollToTop />')
    else:
        # پیدا کردن داخل Routes
        app = app.replace('<Routes>', '<Routes>')
        # اضافه کردن قبل از Routes
        app = app.replace(
            '\n      <Routes>',
            '\n      <ScrollToTop />\n      <Routes>'
        )

    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("✓ ScrollToTop به App.jsx اضافه شد")
    print("ScrollToTop in app:", 'ScrollToTop' in app)
else:
    print("✓ قبلاً موجود بود")
