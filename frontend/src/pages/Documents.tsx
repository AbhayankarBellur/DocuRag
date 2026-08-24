import { useEffect, useRef, useState } from 'react'
import { documentAPI, policyAPI, type PolicyOptions, type WorkflowPreview } from '../services/api'
import StrategySelector from '../components/StrategySelector'
import {
  Upload, Trash2, FileText, ChevronDown, ChevronUp,
  Cpu, Layers, Database, AlertCircle, CheckCircle2, Loader2
} from 'lucide-react'
import { clsx } from 'clsx'

// ─── Helpers ──────────────────────────────────────────────────────────────────
function Badge({ label, color = 'gray' }: { label: string; color?: string }) {
  const colors: Record<string, string> = {
    gray: 'bg-gray-100 text-gray-600',
    indigo: 'bg-indigo-100 text-indigo-700',
    emerald: 'bg-emerald-100 text-emerald-700',
    amber: 'bg-amber-100 text-amber-700',
    rose: 'bg-rose-100 text-rose-700',
    violet: 'bg-violet-100 text-violet-700',
  }
  return (
    <span className={clsx('px-2 py-0.5 rounded-full text-[11px] font-medium', colors[color] ?? colors.gray)}>
      {label}
    </span>
  )
}

const DOMAIN_COLORS: Record<string, string> = {
  technical: 'indigo', legal: 'amber', medical: 'rose',
  financial: 'emerald', academic: 'violet', general: 'gray',
}

// ─── Policy Preview Card ──────────────────────────────────────────────────────
function PolicyPreviewCard({ preview, loading }: { preview: WorkflowPreview | null; loading: boolean }) {
  if (loading) return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 flex items-center gap-3 text-sm text-indigo-600">
      <Loader2 className="w-4 h-4 animate-spin" />
      Analysing document for auto-selection…
    </div>
  )
  if (!preview) return null

  const rows = [
    { label: 'Chunking', value: preview.chunking_strategy, mode: preview.chunking_mode },
    { label: 'Embedding', value: preview.embedding_model.split('/').pop()!, mode: preview.embedding_mode },
    { label: 'Retrieval', value: preview.retrieval_strategy, mode: preview.retrieval_mode },
  ]

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-indigo-700">
        <Cpu className="w-4 h-4" />
        Policy auto-selection preview
        {preview.document_domain && (
          <Badge label={preview.document_domain} color={DOMAIN_COLORS[preview.document_domain] ?? 'gray'} />
        )}
        {preview.document_complexity != null && (
          <Badge label={`complexity ${preview.document_complexity}/5`} color="gray" />
        )}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {rows.map(r => (
          <div key={r.label} className="bg-white rounded-lg p-2.5 border border-indigo-100">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">{r.label}</p>
            <p className="text-sm font-semibold text-gray-800 mt-0.5">{r.value}</p>
            <p className="text-[10px] text-indigo-500 mt-0.5">{r.mode}</p>
          </div>
        ))}
      </div>
      {Object.keys(preview.auto_rationale).length > 0 && (
        <details className="text-xs text-gray-600">
          <summary className="cursor-pointer text-indigo-600 font-medium select-none">
            Why these strategies?
          </summary>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            {Object.entries(preview.auto_rationale).map(([k, v]) => (
              <li key={k}><span className="font-medium capitalize">{k}:</span> {v}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Documents() {
  const [documents, setDocuments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)

  // Strategy config
  const [options, setOptions] = useState<PolicyOptions | null>(null)
  const [showOverrides, setShowOverrides] = useState(false)
  const [chunking, setChunking] = useState('auto')
  const [embedding, setEmbedding] = useState('auto')

  // Policy preview state
  const [preview, setPreview] = useState<WorkflowPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [pendingTitle, setPendingTitle] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadDocuments()
    policyAPI.options().then(r => setOptions(r.data)).catch(() => {})
  }, [])

  const loadDocuments = async () => {
    try {
      const r = await documentAPI.list()
      setDocuments(r.data)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  // When file is picked, fetch a policy preview using the first 2000 chars
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setPendingFile(file)
    setPendingTitle(file.name)
    setUploadError(null)
    setUploadSuccess(null)
    setPreview(null)

    // Read a text sample for preview (only works for text files; binary gives empty)
    try {
      const text = await file.text()
      const sample = text.slice(0, 2000)
      if (sample.trim()) {
        setPreviewLoading(true)
        const r = await policyAPI.preview({
          document_text_sample: sample,
          chunking_strategy: chunking === 'auto' ? undefined : chunking,
          embedding_model: embedding === 'auto' ? undefined : embedding,
        })
        setPreview(r.data)
      }
    } catch { /* preview is best-effort */ }
    finally { setPreviewLoading(false) }
  }

  const handleUpload = async () => {
    if (!pendingFile) return
    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)
    try {
      await documentAPI.upload(pendingFile, {
        title: pendingTitle || pendingFile.name,
        chunking_strategy: chunking,
        embedding_model: embedding,
      })
      setUploadSuccess(`"${pendingTitle || pendingFile.name}" uploaded and processed.`)
      setPendingFile(null)
      setPendingTitle('')
      setPreview(null)
      if (fileRef.current) fileRef.current.value = ''
      loadDocuments()
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail ?? 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document and all its vectors?')) return
    try {
      await documentAPI.delete(id)
      loadDocuments()
    } catch { /* ignore */ }
  }

  const chunkingOpts = options?.chunking_strategies ?? ['auto', 'fixed', 'recursive', 'semantic', 'section']
  const embeddingOpts = options?.embedding_models ?? ['auto', 'BAAI/bge-small-en-v1.5', 'BAAI/bge-base-en-v1.5', 'BAAI/bge-large-en-v1.5']

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Documents</h1>

      {/* ── Upload Panel ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-5">
        <h2 className="font-semibold text-gray-800 flex items-center gap-2">
          <Upload className="w-4 h-4 text-indigo-500" /> Upload a Document
        </h2>

        {/* File picker */}
        <div className="flex gap-3 items-start flex-wrap">
          <label className="flex-1 min-w-48 cursor-pointer">
            <div className={clsx(
              'border-2 border-dashed rounded-xl p-5 text-center transition-colors',
              pendingFile ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 hover:border-indigo-300'
            )}>
              <FileText className="w-8 h-8 mx-auto mb-2 text-gray-400" />
              {pendingFile
                ? <p className="text-sm font-medium text-indigo-700">{pendingFile.name}</p>
                : <p className="text-sm text-gray-500">Click to choose a file</p>
              }
              <p className="text-xs text-gray-400 mt-1">PDF · DOCX · PPTX · TXT · MD · HTML</p>
            </div>
            <input
              ref={fileRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.pptx,.txt,.md,.html"
              onChange={handleFileChange}
              disabled={uploading}
            />
          </label>

          {pendingFile && (
            <div className="flex-1 min-w-48 space-y-2">
              <label className="text-xs font-semibold text-gray-600">Title (optional)</label>
              <input
                type="text"
                value={pendingTitle}
                onChange={e => setPendingTitle(e.target.value)}
                placeholder="Document title"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          )}
        </div>

        {/* Policy preview */}
        <PolicyPreviewCard preview={preview} loading={previewLoading} />

        {/* Override section */}
        <div>
          <button
            type="button"
            onClick={() => setShowOverrides(v => !v)}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-indigo-600 transition-colors"
          >
            {showOverrides ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {showOverrides ? 'Hide' : 'Override'} processing strategies
          </button>

          {showOverrides && (
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
              <StrategySelector
                label="Chunking Strategy"
                value={chunking}
                options={chunkingOpts}
                onChange={setChunking}
                policyValue={preview?.chunking_strategy}
              />
              <StrategySelector
                label="Embedding Model"
                value={embedding}
                options={embeddingOpts}
                onChange={setEmbedding}
                policyValue={preview?.embedding_model}
              />
            </div>
          )}
        </div>

        {/* Status messages */}
        {uploadError && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-3 border border-red-200">
            <AlertCircle className="w-4 h-4 shrink-0" /> {uploadError}
          </div>
        )}
        {uploadSuccess && (
          <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 rounded-lg p-3 border border-emerald-200">
            <CheckCircle2 className="w-4 h-4 shrink-0" /> {uploadSuccess}
          </div>
        )}

        {/* Upload button */}
        {pendingFile && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium text-sm transition-colors disabled:opacity-60"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {uploading ? 'Processing…' : 'Upload & Process'}
          </button>
        )}
      </div>

      {/* ── Document List ── */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading…</div>
      ) : documents.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm text-center py-14">
          <FileText className="w-12 h-12 mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">No documents yet. Upload your first one above.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <h2 className="font-semibold text-gray-700 flex items-center gap-2">
            <Layers className="w-4 h-4 text-gray-400" />
            {documents.length} document{documents.length !== 1 ? 's' : ''}
          </h2>
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm px-5 py-4 flex items-start justify-between gap-4"
            >
              <div className="flex items-start gap-3 min-w-0">
                <div className="mt-0.5 p-2 bg-indigo-50 rounded-lg shrink-0">
                  <Database className="w-4 h-4 text-indigo-500" />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-gray-900 truncate">{doc.title}</p>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    <Badge label={doc.document_type?.toUpperCase() ?? '—'} color="gray" />
                    {doc.chunk_count > 0 && (
                      <Badge label={`${doc.chunk_count} chunks`} color="indigo" />
                    )}
                    {doc.chunking_strategy && (
                      <Badge label={doc.chunking_strategy} color="indigo" />
                    )}
                    {doc.embedding_model && (
                      <Badge label={doc.embedding_model.split('/').pop()!} color="violet" />
                    )}
                    {doc.domain && (
                      <Badge label={doc.domain} color={DOMAIN_COLORS[doc.domain] ?? 'gray'} />
                    )}
                    {doc.complexity_score != null && (
                      <Badge label={`complexity ${doc.complexity_score}/5`} color="amber" />
                    )}
                    {doc.status && (
                      <Badge
                        label={doc.status}
                        color={doc.status === 'completed' ? 'emerald' : doc.status === 'failed' ? 'rose' : 'amber'}
                      />
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="shrink-0 p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
