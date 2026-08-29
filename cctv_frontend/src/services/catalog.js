import api from './api'

export const catalogService = {
  getCategories: () =>
    api.get('/catalog/categories/').then(r => r.data),

  getCategory: (slug) =>
    api.get(`/catalog/categories/${slug}/`).then(r => r.data),

  getCategoryProducts: (slug, params = {}) =>
    api.get('/catalog/products/', { params: { ...params, category_slug: slug } }).then(r => r.data),

  getProducts: (params = {}) =>
    api.get('/catalog/products/', { params }).then(r => r.data),

  getProduct: (slug) =>
    api.get(`/catalog/products/${slug}/`).then(r => r.data),

  searchProducts: (q) =>
    api.get('/catalog/products/search/', { params: { q } }).then(r => r.data),

  getBrands: () =>
    api.get('/catalog/products/brands/').then(r => r.data),

  getExchangeRate: () =>
    api.get('/catalog/exchange-rate/').then(r => r.data),
}
