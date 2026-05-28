import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'AdminOrdersPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن ستون updated_by به جدول
old_headers = "['شماره سفارش', 'مشتری', 'موبایل', 'مبلغ', 'وضعیت سفارش', 'وضعیت ارسال', 'کد رهگیری', 'عملیات']"
new_headers = "['شماره سفارش', 'مشتری', 'موبایل', 'مبلغ', 'وضعیت سفارش', 'وضعیت ارسال', 'کد رهگیری', 'آپدیت توسط', 'عملیات']"

content = content.replace(old_headers, new_headers)

# اضافه کردن ستون updated_by قبل از عملیات
old_td = '''                    <td style={{ padding: '10px 12px' }}>
                      <button onClick={() => setSelected(o)}'''

new_td = '''                    <td style={{ padding: '10px 12px', fontSize: 11 }}>
                      {o.updated_by ? (
                        <div>
                          <div style={{ color: '#fff' }}>{o.updated_by}</div>
                          <div style={{ color: 'var(--color-text-secondary)', fontSize: 10 }}>{o.status_updated_at}</div>
                        </div>
                      ) : <span style={{ color: 'var(--color-text-secondary)' }}>—</span>}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <button onClick={() => setSelected(o)}'''

content = content.replace(old_td, new_td)

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ AdminOrdersPage آپدیت شد")
