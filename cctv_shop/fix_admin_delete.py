import os

with open(os.path.join('apps','catalog','admin.py'), encoding='utf-8') as f:
    content = f.read()

# اضافه کردن actions به ProductAdmin
old = '''    list_display    = ["name", "category", "is_active", "is_featured"]
    list_filter     = ["is_active", "is_featured", "category__category_type", "category"]
    search_fields   = ["name", "brand", "model_number"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal   = ["compatible_with"]
    list_editable       = ["is_active"]
    readonly_fields     = ["created_at", "updated_at"]
    inlines             = [ProductImageInline, ProductVariantInline]'''

new = '''    list_display    = ["name", "category", "brand", "is_active", "is_featured"]
    list_filter     = ["is_active", "is_featured", "category__category_type", "category"]
    search_fields   = ["name", "brand", "model_number"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal   = ["compatible_with"]
    list_editable       = ["is_active"]
    readonly_fields     = ["created_at", "updated_at"]
    inlines             = [ProductImageInline, ProductVariantInline]
    actions             = ["delete_selected"]'''

content = content.replace(old, new)

with open(os.path.join('apps','catalog','admin.py'), 'w', encoding='utf-8') as f:
    f.write(content)
print("OK - admin.py updated")
print("حالا بزنید: python manage.py runserver")
