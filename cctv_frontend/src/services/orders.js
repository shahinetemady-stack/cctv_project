import api from './api'

export const orderService = {
  // سبد عمومی
  getCart: () =>
    api.get('/orders/cart/').then(r => r.data),

  addToCart: (variant_id, quantity = 1, settlement_type = 'cash') =>
    api.post('/orders/cart/', { variant_id, quantity, settlement_type }).then(r => r.data),

  addPackageToCart: (package_id, quantity = 1) =>
    api.post('/orders/cart/', { package_id, quantity }).then(r => r.data),

  removePackageFromCart: (package_id) =>
    api.delete('/orders/cart/', { data: { package_id } }).then(r => r.data),

  removeFromCart: (variant_id, settlement_type = null) =>
    api.delete('/orders/cart/', { data: { variant_id, settlement_type } }).then(r => r.data),

  checkout: (shipping_address = '', shipping_method = 'courier', freight_company = '') =>
    api.post('/orders/cart/checkout/', { shipping_address, shipping_method, freight_company }).then(r => r.data),

  // سبد استعلام
  getInquiryCart: () =>
    api.get('/orders/inquiry-cart/').then(r => r.data),

  addToInquiryCart: (variant_id, quantity = 1, settlement_type = 'cash') =>
    api.post('/orders/inquiry-cart/', { variant_id, quantity, settlement_type }).then(r => r.data),

  removeFromInquiryCart: (variant_id, settlement_type = null) =>
    api.delete('/orders/inquiry-cart/', { data: { variant_id, settlement_type } }).then(r => r.data),

  submitInquiry: (notes = '') =>
    api.post('/orders/inquiry-cart/submit/', { notes }).then(r => r.data),

  // سفارش‌ها
  getOrders: () =>
    api.get('/orders/').then(r => r.data),

  getOrder: (order_number) =>
    api.get(`/orders/${order_number}/`).then(r => r.data),

  cancelOrder: (order_number) =>
    api.post(`/orders/${order_number}/cancel/`).then(r => r.data),

  // تسویه معوقه مشتری — { count, total }
  getMyOverdue: () =>
    api.get('/orders/my-overdue/').then(r => r.data),

  // فیش‌های واریزی مشتری
  getMyReceipts: () =>
    api.get('/orders/my-receipts/').then(r => r.data),

  // ثبت فیش واریزی (multipart) — تصویر سمت سرور فشرده می‌شود
  uploadReceipt: (order_number, formData) =>
    api.post(`/orders/${order_number}/receipts/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data),
}

export const paymentService = {
  requestPayment: (order_number) =>
    api.post('/payment/bank/request/', { order_number }).then(r => r.data),

  getStatus: (order_number) =>
    api.get(`/payment/status/${order_number}/`).then(r => r.data),
}
