import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post('/api/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/api/auth/login', data),
  logout: () => api.post('/api/auth/logout'),
  me: () => api.get('/api/auth/me')
}

// ─── Documents ───────────────────────────────────────────────────────────────
export interface UploadOptions {
  title?: string
  folder_id?: string
  /** 'auto' lets the policy engine decide; or pass explicit value */
  chunking_strategy?: string
  /** 'auto' lets the policy engine decide; or pass explicit model name */
  embedding_model?: string
  vector_store?: string
}

export const documentAPI = {
  upload: (file: File, opts: UploadOptions = {}) => {
    const formData = new FormData()
    formData.append('file', file)
    if (opts.title) formData.append('title', opts.title)
    if (opts.folder_id) formData.append('folder_id', opts.folder_id)
    formData.append('chunking_strategy', opts.chunking_strategy ?? 'auto')
    formData.append('embedding_model', opts.embedding_model ?? 'auto')
    formData.append('vector_store', opts.vector_store ?? 'chroma')
    return api.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  list: (skip = 0, limit = 100) =>
    api.get(`/api/documents/list?skip=${skip}&limit=${limit}`),
  get: (id: string) => api.get(`/api/documents/${id}`),
  delete: (id: string) => api.delete(`/api/documents/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api.put(`/api/documents/${id}`, data)
}

// ─── Queries ─────────────────────────────────────────────────────────────────
export interface QueryOptions {
  question: string
  document_id?: string
  folder_id?: string
  /** 'auto' or explicit: similarity | hybrid | mmr */
  retrieval_strategy?: string
  /** 'auto' or explicit: bm25 | cross_encoder | cohere | none */
  reranking_strategy?: string
  /** 'auto' or explicit: factual_qa | analysis | comparison | creative */
  prompt_template?: string
  /** 'auto' or explicit model name */
  embedding_model?: string
  /** basic | intermediate | advanced | expert */
  reasoning_level?: string
  n_results?: number
}

export const queryAPI = {
  create: (data: QueryOptions) => api.post('/api/queries/', data),
  history: (skip = 0, limit = 100) =>
    api.get(`/api/queries/history?skip=${skip}&limit=${limit}`),
  get: (id: string) => api.get(`/api/queries/${id}`),
  batch: (data: { queries: QueryOptions[]; deferred?: boolean }) =>
    api.post('/api/batch', data)
}

// ─── Policy ──────────────────────────────────────────────────────────────────
export interface WorkflowPreviewRequest {
  query?: string
  document_text_sample?: string
  chunking_strategy?: string
  embedding_model?: string
  retrieval_strategy?: string
  reranking_strategy?: string
  prompt_template?: string
}

export interface WorkflowPreview {
  chunking_strategy: string
  chunking_mode: string
  embedding_model: string
  embedding_mode: string
  retrieval_strategy: string
  retrieval_mode: string
  reranking_strategy: string | null
  reranking_mode: string
  prompt_template: string
  prompt_mode: string
  generation_params: Record<string, number>
  auto_rationale: Record<string, string>
  document_domain: string | null
  document_complexity: number | null
  query_intent: string | null
  query_complexity: number | null
}

export interface PolicyOptions {
  chunking_strategies: string[]
  embedding_models: string[]
  retrieval_strategies: string[]
  reranking_strategies: string[]
  vector_stores: string[]
}

export const policyAPI = {
  options: () => api.get<PolicyOptions>('/api/policy/options'),
  preview: (data: WorkflowPreviewRequest) =>
    api.post<WorkflowPreview>('/api/policy/workflow-preview', data)
}

// ─── Evaluation ───────────────────────────────────────────────────────────────
export interface GoldenItem {
  question: string
  ground_truth: string
  document_id?: string
}

export interface EvalRunResult {
  condition: string
  config: Record<string, string>
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number | null
  overall_score: number
  avg_tokens: number
  avg_latency_ms: number
}

export const evalAPI = {
  run: (data: { golden_items: GoldenItem[]; conditions?: string[] }) =>
    api.post<{ run_id: string; results: EvalRunResult[] }>(
      '/api/admin/evaluate',
      data
    ),
  history: () =>
    api.get<{ run_id: string; created_at: string; results: EvalRunResult[] }[]>(
      '/api/admin/evaluate/history'
    )
}

export default api
