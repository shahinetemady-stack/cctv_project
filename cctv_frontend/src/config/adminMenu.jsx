// ─── منوی پنل مدیریت ──────────────────────────────────────────
// این فایل در Layout.jsx و Header.jsx استفاده می‌شه
// آیکون‌ها: SVG stroke با currentColor — رنگ از والد ارث می‌برند

const I = ({ children }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
)

const icons = {
  dashboard: (
    <I><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></I>
  ),
  orders: (
    <I><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></I>
  ),
  saleInvoice: (
    <I><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/></I>
  ),
  kardex: (
    <I><path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5"/><path d="M12 13v8"/></I>
  ),
  purchases: (
    <I><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></I>
  ),
  contacts: (
    <I><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></I>
  ),
  payments: (
    <I><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/><path d="M5 15h4"/></I>
  ),
  bank: (
    <I><path d="M12 3l9 6H3z"/><path d="M5 9v9"/><path d="M9.5 9v9"/><path d="M14.5 9v9"/><path d="M19 9v9"/><path d="M3 21h18"/></I>
  ),
  financial: (
    <I><path d="M3 3v18h18"/><path d="M7 15l4-6 4 3 5-8"/></I>
  ),
  balance: (
    <I><path d="M12 3v18"/><path d="M5 7l7-4 7 4"/><path d="M5 7l-3 7a4 4 0 0 0 6 0z"/><path d="M19 7l-3 7a4 4 0 0 0 6 0z"/></I>
  ),
  excel: (
    <I><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M12 11v6"/><path d="M9 14h6"/></I>
  ),
  roles: (
    <I><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></I>
  ),
  products: (
    <I><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></I>
  ),
  categories: (
    <I><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></I>
  ),
  fields: (
    <I><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></I>
  ),
  backup: (
    <I><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></I>
  ),
  returns: (
    <I><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></I>
  ),
  sms: (
    <I><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></I>
  ),
}

const ADMIN_MENU = [
  { label: 'داشبورد',            path: '/admin/dashboard',         perm: 'dashboard_view', icon: icons.dashboard },
  { label: 'لیست قیمت',          path: '/admin/pricing',           perm: 'products_edit',  icon: icons.financial },
  { label: 'سفارشات',            path: '/admin/orders-management', perm: 'sale_view',      icon: icons.orders,    badgeKey: 'orders' },
  { label: 'فیش‌های واریزی',     path: '/admin/receipts',          perm: 'sale_payment',   icon: icons.payments, badgeKey: 'receipts' },
  { label: 'مطالبات تاریخ‌گذشته', path: '/admin/aging',            perm: 'reports_view',   icon: icons.balance },
  { label: 'فاکتور فروش',        path: '/admin/sales',             perm: 'sale_view',      icon: icons.saleInvoice, badgeKey: 'salesDue' },
  { label: 'فاکتور خرید',        path: '/admin/purchases',         perm: 'purchase_view',  icon: icons.purchases },
  { label: 'دریافت و پرداخت',    path: '/admin/payments',          perm: 'reports_view',   icon: icons.payments },
  { label: 'برگشت از فروش و خرید', path: '/admin/returns',         perm: 'return_view',    icon: icons.returns },
  { label: 'طرف حساب‌ها',       path: '/admin/contacts',          perm: 'contacts_view',  icon: icons.contacts, badgeKey: 'partners' },
  // ─── گروه تاشو: گزارشات ───
  {
    label: 'گزارشات',
    icon: icons.financial,
    children: [
      { label: 'گزارش رد سفارش‌ها', path: '/admin/reject-report', perm: 'sale_view',     icon: icons.orders },
      { label: 'بانک',              path: '/admin/banks',         perm: 'balance_view',  icon: icons.bank },
      { label: 'کاردکس موجودی',     path: '/admin/kardex',        perm: 'kardex_view',   icon: icons.kardex },
      { label: 'انبارها',           path: '/admin/warehouses',    perm: 'kardex_view',   icon: icons.kardex },
    ],
  },
  // ─── گروه تاشو: رسیدگی به محتویات سایت ───
  {
    label: 'رسیدگی به محتویات سایت',
    icon: icons.products,
    children: [
      { label: 'محتوی',          path: '/admin/content',  perm: 'products_edit', icon: icons.fields },
      { label: 'مدیریت محصولات', path: '/admin/products', perm: 'products_edit', icon: icons.products },
      { label: 'پکیج‌ها',        path: '/admin/packages', perm: 'products_edit', icon: icons.kardex },
    ],
  },
  // ─── گروه تاشو در انتهای منو — آیتم‌های کم‌کاربردتر ───
  {
    label: 'پنل ادمین',
    icon: icons.roles,
    children: [
      { label: 'لاگ فعالیت‌ها',      path: '/admin/logs',            perm: 'users_view',    icon: icons.roles },
      { label: 'بک‌آپ سیستم',        path: '/admin/backup',          perm: 'reports_view',  icon: icons.backup, superuserOnly: true },
      { label: 'نقش‌ها و پرسنل',     path: '/admin/roles',           perm: 'users_edit',    icon: icons.roles },
      { label: 'ویژگی‌های دسته‌ها',  path: '/admin/category-fields', perm: 'products_edit', icon: icons.fields },
      { label: 'مدیریت دسته‌بندی محصولات', path: '/admin/categories', perm: 'products_edit', icon: icons.categories },
      { label: 'گزارش مالی پیشرفته', path: '/admin/financial',       perm: 'reports_view',  icon: icons.financial },
      { label: 'مازاد تقاضا',        path: '/admin/shortage',        perm: 'kardex_view',   icon: icons.kardex },
      { label: 'تنظیمات پیامک',      path: '/admin/sms-settings',    superuserOnly: true,   icon: icons.sms },
      { label: 'کمپین پیامکی',       path: '/admin/sms-campaign',    superuserOnly: true,   icon: icons.sms },
    ],
  },
]

// ─── فیلتر منو بر اساس دسترسی — گروه‌ها هم بر اساس فرزندانِ قابل‌مشاهده فیلتر می‌شوند ───
const itemVisible = (item, perms, isSuperuser) => {
  if (item.superuserOnly) return isSuperuser
  if (item.perm && !isSuperuser && !perms.includes(item.perm)) return false
  return true
}

export function filterAdminMenu(perms, isSuperuser) {
  return ADMIN_MENU.map(item => {
    if (!item.children) return itemVisible(item, perms, isSuperuser) ? item : null
    const children = item.children.filter(c => itemVisible(c, perms, isSuperuser))
    return children.length ? { ...item, children } : null
  }).filter(Boolean)
}

export default ADMIN_MENU
