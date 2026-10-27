import api from './api'

// ─── سرویس استودیو محتوا (/api/publisher/) ───────────────────
// تولید کپشن با LLM و ساخت ویدیو با FFmpeg زمان‌برند — timeout پیش‌فرض
// ۱۵ ثانیه‌ای axios برایشان کم است و جداگانه بزرگ‌تر تنظیم شده است
export const contentStudioService = {
  posts: (params = {}) =>
    api.get('/publisher/posts/', { params }).then(r => r.data),

  platforms: () =>
    api.get('/publisher/platforms/').then(r => r.data),

  createIdea: (payload) =>
    api.post('/publisher/ideas/', payload, { timeout: 120000 }).then(r => r.data),

  approvePost: (id, payload = {}) =>
    api.post(`/publisher/posts/${id}/approve/`, payload).then(r => r.data),

  rejectPost: (id) =>
    api.post(`/publisher/posts/${id}/reject/`).then(r => r.data),

  buildMedia: (id, force = false) =>
    api.post(`/publisher/posts/${id}/build-media/${force ? '?force=1' : ''}`, null, { timeout: 300000 }).then(r => r.data),

  // ساخت هوک AI در بک‌گراند انجام می‌شود (202) — نتیجه با polling روی پست دیده می‌شود
  generateHook: (id) =>
    api.post(`/publisher/posts/${id}/generate-hook/`).then(r => r.data),

  setStyle: (id, videoStyle) =>
    api.post(`/publisher/posts/${id}/style/`, { video_style: videoStyle }).then(r => r.data),

  settings: () =>
    api.get('/publisher/settings/').then(r => r.data),

  saveSettings: (payload) =>
    api.post('/publisher/settings/', payload).then(r => r.data),

  music: () =>
    api.get('/publisher/music/').then(r => r.data),

  insights: () =>
    api.get('/publisher/insights/').then(r => r.data),

  uploadMusic: (formData) =>
    api.post('/publisher/music/', formData, { timeout: 120000 }).then(r => r.data),
}
