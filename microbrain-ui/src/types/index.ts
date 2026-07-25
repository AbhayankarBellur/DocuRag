export interface User {
  id: string;
  email: string;
  full_name?: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Document {
  id: string;
  user_id: string;
  title: string;
  filename: string;
  document_type: 'pdf' | 'docx' | 'pptx' | 'txt' | 'md' | 'html';
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  chunking_strategy?: string;
  embedding_model?: string;
  vector_store?: string;
  metadata?: Record<string, any>;
  domain?: string;
  complexity_score?: number;
  language?: string;
  created_at: string;
  updated_at?: string;
  processed_at?: string;
}

export interface Query {
  id: string;
  user_id: string;
  question: string;
  document_id?: string;
  answer?: string;
  sources?: Array<{
    id: string;
    text: string;
  }>;
  retrieval_strategy?: string;
  reranking_strategy?: string;
  embedding_model?: string;
  generation_model?: string;
  prompt_template?: string;
  retrieval_time?: number;
  generation_time?: number;
  total_time?: number;
  token_usage?: number;
  status: 'processing' | 'completed' | 'failed';
  error_message?: string;
  created_at: string;
  updated_at?: string;
}

export interface QueryCreate {
  question: string;
  document_id?: string;
  retrieval_strategy?: string;
  reranking_strategy?: string;
  prompt_template?: string;
  reasoning_level?: 'basic' | 'intermediate' | 'advanced' | 'expert';
  n_results?: number;
  folder_id?: string;
}

export interface Folder {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  color?: string;
  parent_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface FolderCreate {
  name: string;
  description?: string;
  color?: string;
  parent_id?: string;
}

export interface BatchQueryCreate {
  queries: QueryCreate[];
  deferred?: boolean;
}
