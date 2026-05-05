import api from './api'

export const authService = {
  register: (data) =>
    api.post('/users/auth/register/', data).then(r => r.data),

  login: (data) =>
    api.post('/users/auth/login/', data).then(r => r.data),

  logout: (refresh) =>
    api.post('/users/auth/logout/', { refresh }),

  getMe: () =>
    api.get('/users/me/').then(r => r.data),

  updateMe: (data) =>
    api.put('/users/me/', data).then(r => r.data),

  changePassword: (data) =>
    api.post('/users/me/change-password/', data).then(r => r.data),

  registerPartner: (data) =>
    api.post('/users/me/register-partner/', data).then(r => r.data),
}
