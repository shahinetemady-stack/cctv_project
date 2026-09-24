import api from './api'

// ─── سرویس مخاطبان تبلیغاتی (/api/leads/) ───────────────────
export const leadsService = {
  list: (params) =>
    api.get('/leads/', { params }).then(r => r.data),

  meta: () =>
    api.get('/leads/meta/').then(r => r.data),

  create: (payload) =>
    api.post('/leads/', payload).then(r => r.data),

  update: (id, payload) =>
    api.patch(`/leads/${id}/`, payload).then(r => r.data),

  remove: (id) =>
    api.delete(`/leads/${id}/`),

  importText: (payload) =>
    api.post('/leads/import/', payload).then(r => r.data),

  // دانلود CSV — چون پاسخ فایل است باید blob گرفته شود و با لینک موقت دانلود شود
  async exportCsv(params) {
    const res = await api.get('/leads/export/', { params, responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'leads.csv'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },

  campaigns: () =>
    api.get('/leads/campaigns/').then(r => r.data),

  createCampaign: (payload) =>
    api.post('/leads/campaigns/', payload).then(r => r.data),

  sendCampaign: (id) =>
    api.post(`/leads/campaigns/${id}/send/`).then(r => r.data),

  getSettings: () =>
    api.get('/leads/settings/').then(r => r.data),

  saveSettings: (payload) =>
    api.put('/leads/settings/', payload).then(r => r.data),

  runScraper: (source) =>
    api.post(`/leads/run/${source}/`).then(r => r.data),
}
