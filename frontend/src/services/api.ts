import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const authAPI = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post('/api/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/api/auth/login', data),
  logout: () => api.post('/api/auth/logout'),
  me: () => api.get('/api/auth/me')
}

export const documentAPI = {
  upload: (file: File, title?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (title) formData.append('title', title)
    return api.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  list: (skip = 0, limit = 100) =>
    api.get(`/api/documents/list?skip=${skip}&limit=${limit}`),
  get: (id: string) => api.get(`/api/documents/${id}`),
  delete: (id: string) => api.delete(`/api/documents/${id}`),
  update: (id: string, data: any) => api.put(`/api/documents/${id}`, data)
}

export const queryAPI = {
  create: (data: { question: string; document_id?: string }) =>
    api.post('/api/queries/', data),
  history: (skip = 0, limit = 100) =>
    api.get(`/api/queries/history?skip=${skip}&limit=${limit}`),
  get: (id: string) => api.get(`/api/queries/${id}`),
  batch: (data: { queries: any[]; deferred?: boolean }) =>
    api.post('/api/queries/batch', data)
}

export default api
