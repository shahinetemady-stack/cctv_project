import api from './api'

export const orderService = {
  // سبد عمومی
  getCart: () =>
    api.get('/orders/cart/').then(r => r.data),

  addToCart: (variant_id, quantity = 1) =>
    api.post('/orders/cart/', { variant_id, quantity }).then(r => r.data),

  removeFromCart: (variant_id) =>
    api.delete('/orders/cart/', { data: { variant_id } }).then(r => r.data),

  checkout: (shipping_address = '', shipping_method = 'post', freight_company = '') =>
    api.post('/orders/cart/checkout/', { shipping_address, shipping_method, freight_company }).then(r => r.data),

  // سبد استعلام
  getInquiryCart: () =>
    api.get('/orders/inquiry-cart/').then(r => r.data),

  addToInquiryCart: (variant_id, quantity = 1) =>
    api.post('/orders/inquiry-cart/', { variant_id, quantity }).then(r => r.data),

  removeFromInquiryCart: (variant_id) =>
    api.delete('/orders/inquiry-cart/', { data: { variant_id } }).then(r => r.data),

  submitInquiry: (notes = '') =>
    api.post('/orders/inquiry-cart/submit/', { notes }).then(r => r.data),

  // سفارش‌ها
  getOrders: () =>
    api.get('/orders/').then(r => r.data),

  getOrder: (order_number) =>
    api.get(`/orders/${order_number}/`).then(r => r.data),

  cancelOrder: (order_number) =>
    api.post(`/orders/${order_number}/cancel/`).then(r => r.data),
}

export const paymentService = {
  requestPayment: (order_number) =>
    api.post('/payment/bank/request/', { order_number }).then(r => r.data),

  getStatus: (order_number) =>
    api.get(`/payment/status/${order_number}/`).then(r => r.data),
}
