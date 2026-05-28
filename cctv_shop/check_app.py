import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
app_path = os.path.join(FRONTEND, 'App.jsx')

with open(app_path, encoding='utf-8') as f:
    app = f.read()

# نمایش ۲۰ خط اول
lines = app.split('\n')
print("=== ۲۰ خط اول ===")
for i, l in enumerate(lines[:20], 1):
    print(f"{i}: {l}")

print("\nScrollToTop in file:", 'ScrollToTop' in app)
print("BrowserRouter in file:", 'BrowserRouter' in app)
print("Router tag:", '<Router' in app)

# پیدا کردن محل router
for i, l in enumerate(lines, 1):
    if 'Router' in l or 'Routes' in l:
        print(f"line {i}: {l.strip()}")
