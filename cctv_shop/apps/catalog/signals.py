"""
apps/catalog/signals.py
───────────────────────
ثبت تغییرات محصول/واریانت/تصویر در کش برای اطلاع‌رسانی بعدی به وب‌هوک ترب
(خود وب‌هوک داخل سیگنال صدا زده نمی‌شود — کامند push_torob_updates ارسال می‌کند).
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Product, ProductImage, ProductVariant
from .torob import mark_product_dirty


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def product_torob_dirty(sender, instance, **kwargs):
    mark_product_dirty(instance)


@receiver(post_save, sender=ProductVariant)
@receiver(post_delete, sender=ProductVariant)
def variant_torob_dirty(sender, instance, **kwargs):
    mark_product_dirty(instance.product)


@receiver(post_save, sender=ProductImage)
@receiver(post_delete, sender=ProductImage)
def image_torob_dirty(sender, instance, **kwargs):
    mark_product_dirty(instance.product)
