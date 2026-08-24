import { useEffect, useRef, useState } from 'react'
import { queryAPI, policyAPI, type PolicyOptions, type WorkflowPreview, type QueryOptions } from '../services/api'
import StrategySelector from '../components/StrategySelector'
import {
  Send, MessageSquare, ChevronDown, ChevronUp,
  Cpu, Clock, Hash, Zap, BookOpen, AlertCircle, Loader2, Info
} from 'lucide-react'
import { clsx } from 'clsx'

// ─── Helpers ──────────────────────────────────────────────────────────────────
function MetaBadge({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-gray-100 text-xs text-gray-600 font-medium">
      {icon}
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-800">{value}</span>
    </span>
  )
}

function ModeChip({ mode }: { mode: string }) {
  return (
    <span className={clsx(
      'px-1.5 py-0.5 rounded text-[10px] font-semibold',
      mode === 'auto' ? 'bg-indigo-100 text-indigo-600' : 'bg-amber-100 text-amber-700'
    )}>
      {mode}
    </span>
  )
}

// ─── Workflow Trace Panel ─────────────────────────────────────────────────────
function WorkflowTrace({ item }: { item: any }) {
  const [open, setOpen] = useState(false)
  const trace = item.workflow_trace as Record<string, any> | undefined
  if (!trace) return null

  const strategies = [
    { key: 'retrieval_strategy', label: 'Retrieval', mode: trace.retrieval_mode },
    { key: 'reranking_strategy', label: 'Reranking', mode: trace.reranking_mode },
    { key: 'embedding_model', label: 'Embedding', mode: trace.embedding_mode },
    { key: 'prompt_template', label: 'Template', mode: trace.prompt_mode },
  ]

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
      >
        <Cpu className="w-3.5 h-3.5" />
        Policy trace
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          <div className="flex flex-wrap gap-2">
            {strategies.map(s => (
              <div key={s.key} className="flex items-center gap-1 bg-gray-50 rounded-lg px-2 py-1">
                <span className="text-[10px] text-gray-400 font-semibold uppercase">{s.label}</span>
                <span className="text-xs font-medium text-gray-700">
                  {String(trace[s.key] ?? '—').split('/').pop()}
                </span>
                <ModeChip mode={s.mode ?? 'auto'} />
              </div>
            ))}
          </div>
          {trace.auto_rationale && Object.keys(trace.auto_rationale).length > 0 && (
            <ul className="text-[11px] text-gray-500 space-y-0.5 list-disc list-inside">
              {Object.entries(trace.auto_rationale as Record<string, string>).map(([k, v]) => (
                <li key={k}><span className="font-medium capitalize text-gray-600">{k}:</span> {v}</li>
              ))}
            </ul>
          )}
          {trace.escalated && (
            <p className="text-[11px] text-amber-600 font-medium flex items-center gap-1">
              <Zap className="w-3 h-3" /> Low confidence — retrieval was auto-escalated to {trace.escalated_to}.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Source Chips ─────────────────────────────────────────────────────────────
function Sources({ sources }: { sources: any[] }) {
  const [open, setOpen] = useState(false)
  if (!sources?.length) return null
  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 font-medium"
      >
        <BookOpen className="w-3.5 h-3.5" />
        {sources.length} source{sources.length !== 1 ? 's' : ''}
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && (
        <ul className="mt-2 space-y-1">
          {sources.map((s: any, i: number) => (
            <li key={i} className="text-[11px] text-gray-500 bg-gray-50 rounded-lg p-2 border border-gray-100">
              <span className="font-mono text-gray-400">[{i + 1}]</span> {s.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ─── Live Policy Preview line ─────────────────────────────────────────────────
function LivePolicyHint({ preview, loading }: { preview: WorkflowPreview | null; loading: boolean }) {
  if (loading) return (
    <p className="text-xs text-indigo-500 flex items-center gap-1 animate-pulse">
      <Cpu className="w-3 h-3" /> Analysing query…
    </p>
  )
  if (!preview) return null
  return (
    <p className="text-xs text-indigo-600 flex items-center gap-1">
      <Cpu className="w-3 h-3" />
      Policy would use: <strong>{preview.retrieval_strategy}</strong> retrieval
      {preview.reranking_strategy && <>, <strong>{preview.reranking_strategy}</strong> reranking</>}
      {preview.query_intent && <>, <strong>{preview.query_intent}</strong> template</>}
    </p>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Queries() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<any[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [showConfig, setShowConfig] = useState(false)

  // Strategy config
  const [options, setOptions] = useState<PolicyOptions | null>(null)
  const [retrieval, setRetrieval] = useState('auto')
  const [reranking, setReranking] = useState('auto')
  const [template, setTemplate] = useState('auto')
  const [embeddingModel, setEmbeddingModel] = useState('auto')
  const [reasoningLevel, setReasoningLevel] = useState('intermediate')
  const [nResults, setNResults] = useState(5)

  // Live policy preview
  const [livePreview, setLivePreview] = useState<WorkflowPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    loadHistory()
    policyAPI.options().then(r => setOptions(r.data)).catch(() => {})
  }, [])

  const loadHistory = async () => {
    try {
      const r = await queryAPI.history(0, 50)
      setHistory(r.data)
    } catch { /* ignore */ }
    finally { setHistoryLoading(false) }
  }

  // Debounced live policy preview as the user types
  const handleQuestionChange = (val: string) => {
    setQuestion(val)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (val.trim().length < 6) { setLivePreview(null); return }
    debounceRef.current = setTimeout(async () => {
      try {
        setPreviewLoading(true)
        const r = await policyAPI.preview({
          query: val,
          retrieval_strategy: retrieval === 'auto' ? undefined : retrieval,
          reranking_strategy: reranking === 'auto' ? undefined : reranking,
          prompt_template: template === 'auto' ? undefined : template,
          embedding_model: embeddingModel === 'auto' ? undefined : embeddingModel,
        })
        setLivePreview(r.data)
      } catch { /* ignore */ }
      finally { setPreviewLoading(false) }
    }, 500)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return
    setSending(true)
    setSendError(null)
    try {
      const payload: QueryOptions = {
        question,
        retrieval_strategy: retrieval === 'auto' ? undefined : retrieval,
        reranking_strategy: reranking === 'auto' ? undefined : reranking,
        prompt_template: template === 'auto' ? undefined : template,
        embedding_model: embeddingModel === 'auto' ? undefined : embeddingModel,
        reasoning_level: reasoningLevel,
        n_results: nResults,
      }
      await queryAPI.create(payload)
      setQuestion('')
      setLivePreview(null)
      loadHistory()
    } catch (err: any) {
      setSendError(err?.response?.data?.detail ?? 'Query failed.')
    } finally {
      setSending(false)
    }
  }

  const retrievalOpts = options?.retrieval_strategies ?? ['auto', 'similarity', 'hybrid', 'mmr']
  const rerankingOpts = options?.reranking_strategies ?? ['auto', 'none', 'bm25', 'cross_encoder', 'cohere']
  const templateOpts = ['auto', 'factual_qa', 'analysis', 'comparison', 'creative', 'code_explanation', 'step_by_step', 'critical_thinking']
  const embeddingOpts = options?.embedding_models ?? ['auto', 'BAAI/bge-small-en-v1.5', 'BAAI/bge-base-en-v1.5', 'BAAI/bge-large-en-v1.5']

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Queries</h1>

      {/* ── Query Input Panel ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            ref={inputRef}
            rows={3}
            value={question}
            onChange={e => handleQuestionChange(e.target.value)}
            placeholder="Ask a question about your documents…"
            disabled={sending}
            className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />

          <LivePolicyHint preview={livePreview} loading={previewLoading} />

          {/* Strategy config toggle */}
          <div>
            <button
              type="button"
              onClick={() => setShowConfig(v => !v)}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-indigo-600 transition-colors"
            >
              {showConfig ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {showConfig ? 'Hide' : 'Configure'} retrieval strategies
            </button>

            {showConfig && (
              <div className="mt-3 p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <StrategySelector
                    label="Retrieval Strategy"
                    value={retrieval}
                    options={retrievalOpts}
                    onChange={setRetrieval}
                    policyValue={livePreview?.retrieval_strategy}
                  />
                  <StrategySelector
                    label="Reranking"
                    value={reranking}
                    options={rerankingOpts}
                    onChange={setReranking}
                    policyValue={livePreview?.reranking_strategy ?? 'none'}
                  />
                  <StrategySelector
                    label="Prompt Template"
                    value={template}
                    options={templateOpts}
                    onChange={setTemplate}
                    policyValue={livePreview?.prompt_template}
                  />
                  <StrategySelector
                    label="Embedding Model"
                    value={embeddingModel}
                    options={embeddingOpts}
                    onChange={setEmbeddingModel}
                    policyValue={livePreview?.embedding_model}
                  />
                </div>

                <div className="flex flex-wrap gap-4 pt-2 border-t border-gray-200">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide flex items-center gap-1">
                      Reasoning Level
                      <span className="relative group">
                        <Info className="w-3 h-3 text-gray-400 cursor-help" />
                        <span className="absolute hidden group-hover:block z-50 bottom-5 left-0 w-52 bg-gray-900 text-white text-xs rounded-lg p-2">
                          Controls max tokens and temperature. Expert = longest, most creative.
                        </span>
                      </span>
                    </label>
                    <select
                      value={reasoningLevel}
                      onChange={e => setReasoningLevel(e.target.value)}
                      className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    >
                      {['basic', 'intermediate', 'advanced', 'expert'].map(l => (
                        <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide flex items-center gap-1">
                      Chunks to Retrieve
                      <span className="relative group">
                        <Info className="w-3 h-3 text-gray-400 cursor-help" />
                        <span className="absolute hidden group-hover:block z-50 bottom-5 left-0 w-52 bg-gray-900 text-white text-xs rounded-lg p-2">
                          How many document chunks to retrieve before generating. More = richer context, higher token cost.
                        </span>
                      </span>
                    </label>
                    <input
                      type="number"
                      min={1} max={20}
                      value={nResults}
                      onChange={e => setNResults(Number(e.target.value))}
                      className="w-20 text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {sendError && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-3 border border-red-200">
              <AlertCircle className="w-4 h-4 shrink-0" /> {sendError}
            </div>
          )}

          <button
            type="submit"
            disabled={sending || !question.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium text-sm transition-colors disabled:opacity-50"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {sending ? 'Processing…' : 'Ask'}
          </button>
        </form>
      </div>

      {/* ── History ── */}
      {historyLoading ? (
        <div className="text-center py-12 text-gray-400">Loading history…</div>
      ) : history.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 text-center py-14">
          <MessageSquare className="w-10 h-10 mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400">No queries yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="font-semibold text-gray-700">Query History</h2>
          {history.map((item) => (
            <div key={item.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
              {/* Question */}
              <p className="font-semibold text-gray-900">{item.question}</p>

              {/* Answer */}
              {item.answer && (
                <p className="mt-2 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{item.answer}</p>
              )}
              {item.status === 'failed' && (
                <p className="mt-2 text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" /> {item.error_message ?? 'Query failed'}
                </p>
              )}
              {item.status === 'processing' && (
                <p className="mt-2 text-sm text-indigo-500 flex items-center gap-1 animate-pulse">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing…
                </p>
              )}

              {/* Metadata strip */}
              <div className="mt-3 flex flex-wrap gap-2">
                {item.retrieval_strategy && (
                  <MetaBadge icon={<Zap className="w-3 h-3" />} label="retrieval" value={item.retrieval_strategy} />
                )}
                {item.reranking_strategy && (
                  <MetaBadge icon={<Cpu className="w-3 h-3" />} label="rerank" value={item.reranking_strategy} />
                )}
                {item.prompt_template && (
                  <MetaBadge icon={<BookOpen className="w-3 h-3" />} label="template" value={item.prompt_template} />
                )}
                {item.total_time != null && (
                  <MetaBadge icon={<Clock className="w-3 h-3" />} label="latency" value={`${item.total_time}ms`} />
                )}
                {item.token_usage != null && (
                  <MetaBadge icon={<Hash className="w-3 h-3" />} label="tokens" value={item.token_usage} />
                )}
                {item.generation_model && (
                  <MetaBadge icon={<Cpu className="w-3 h-3" />} label="model" value={item.generation_model.split('/').pop()!} />
                )}
              </div>

              {/* Workflow trace */}
              <WorkflowTrace item={item} />

              {/* Sources */}
              {item.sources && <Sources sources={item.sources} />}

              <p className="mt-3 text-[11px] text-gray-400">
                {new Date(item.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
