import os

models_path = os.path.join('apps', 'core', 'models.py')
with open(models_path, 'r', encoding='utf-8') as f:
    content = f.read()

# اضافه کردن SingletonModel اگر نبود
if 'SingletonModel' not in content:
    singleton = '''

class SingletonModel(models.Model):
    """مدل Singleton — فقط یک نمونه"""
    class Meta:
        abstract = True

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass
'''
    # اضافه کردن بعد از TimeStampedModel
    content = content.replace(
        'class SiteSettings',
        singleton + 'class SiteSettings'
    )
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ SingletonModel اضافه شد")
else:
    print("✓ SingletonModel موجود بود")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
