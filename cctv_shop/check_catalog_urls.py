import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# اول بررسی urls
urls_path = os.path.join('apps', 'catalog', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

print("=== catalog urls ===")
print(urls)
