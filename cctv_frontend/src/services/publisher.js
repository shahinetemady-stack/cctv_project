import api from './api'

// ─── سرویس انتشار چندسکویی (/api/publisher/) ───────────────────
export const publisherService = {
  platforms: () =>
    api.get('/publisher/platforms/').then(r => r.data),

  credentials: () =>
    api.get('/publisher/credentials/').then(r => r.data),

  saveCredentials: (payload) =>
    api.post('/publisher/credentials/save/', payload).then(r => r.data),

  posts: () =>
    api.get('/publisher/posts/').then(r => r.data),

  createPost: (formData) =>
    api.post('/publisher/posts/', formData).then(r => r.data),

  publish: (payload) =>
    api.post('/publisher/publish/', payload).then(r => r.data),

  jobs: () =>
    api.get('/publisher/jobs/').then(r => r.data),

  job: (id) =>
    api.get(`/publisher/jobs/${id}/`).then(r => r.data),

  retryLog: (id) =>
    api.post(`/publisher/logs/${id}/retry/`).then(r => r.data),
}
