import os

with open(os.path.join('apps','catalog','admin.py'), encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '"sku", "purchase_price_cny", "shipping_cost_cny", "profit_percent", "partner_discount_percent", "stock_quantity", "is_active"',
    '"sku", "purchase_price_cny", "shipping_cost_cny", "profit_percent", "stock_quantity", "is_active"'
)

with open(os.path.join('apps','catalog','admin.py'), 'w', encoding='utf-8') as f:
    f.write(content)
print("OK - admin.py fixed")
