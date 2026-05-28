import os

views_path = os.path.join('apps', 'orders', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن inquiry_cart_submit
idx = content.find('inquiry_cart_submit')
while idx >= 0:
    start = content.rfind('\nclass ', 0, idx)
    start2 = content.rfind('\ndef ', 0, idx)
    actual_start = max(start, start2)
    print(f"Found at {idx}:")
    print(content[actual_start:actual_start+300])
    print("---")
    idx = content.find('inquiry_cart_submit', idx+1)
    if idx > 0 and content[idx-10:idx].count('\n') == 0:
        break
