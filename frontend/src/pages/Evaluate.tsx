import { useState } from 'react'
import { evalAPI, type GoldenItem, type EvalRunResult } from '../services/api'
import { Plus, Trash2, Play, BarChart2, AlertCircle, Loader2, Info } from 'lucide-react'
import { clsx } from 'clsx'

// ─── Metric bar ───────────────────────────────────────────────────────────────
function MetricBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span className="font-medium">{label}</span>
        <span className="font-bold text-gray-800">{pct}%</span>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ─── Result card ─────────────────────────────────────────────────────────────
const CONDITION_COLORS: Record<string, string> = {
  auto: 'border-indigo-300 bg-indigo-50',
  similarity: 'border-gray-200 bg-white',
  hybrid_bm25: 'border-emerald-200 bg-emerald-50',
  mmr_cross_encoder: 'border-violet-200 bg-violet-50',
}

function ResultCard({ r }: { r: EvalRunResult }) {
  const borderClass = CONDITION_COLORS[r.condition] ?? 'border-gray-200 bg-white'
  const isWinner = r.overall_score >= 0.75

  return (
    <div className={clsx('rounded-2xl border p-5 space-y-4', borderClass)}>
      <div className="flex justify-between items-start">
        <div>
          <p className="font-semibold text-gray-900 capitalize">
            {r.condition === 'auto' ? '✦ Policy Auto' : r.condition.replace(/_/g, ' + ')}
          </p>
          <div className="flex flex-wrap gap-1 mt-1">
            {Object.entries(r.config).map(([k, v]) => (
              <span key={k} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                {k}: {v}
              </span>
            ))}
          </div>
        </div>
        <div className="text-right">
          <p className={clsx(
            'text-2xl font-black',
            r.overall_score >= 0.75 ? 'text-emerald-600' : r.overall_score >= 0.5 ? 'text-amber-600' : 'text-red-500'
          )}>
            {Math.round(r.overall_score * 100)}
          </p>
          <p className="text-[10px] text-gray-400">overall</p>
          {isWinner && <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-semibold">TOP</span>}
        </div>
      </div>

      <div className="space-y-2.5">
        <MetricBar label="Faithfulness" value={r.faithfulness} color="bg-indigo-400" />
        <MetricBar label="Answer Relevancy" value={r.answer_relevancy} color="bg-violet-400" />
        <MetricBar label="Context Precision" value={r.context_precision} color="bg-emerald-400" />
        {r.context_recall != null && (
          <MetricBar label="Context Recall" value={r.context_recall} color="bg-amber-400" />
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-200">
        <div className="text-center">
          <p className="text-lg font-bold text-gray-800">{Math.round(r.avg_latency_ms)}ms</p>
          <p className="text-[10px] text-gray-400">avg latency</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-gray-800">{Math.round(r.avg_tokens)}</p>
          <p className="text-[10px] text-gray-400">avg tokens</p>
        </div>
      </div>
    </div>
  )
}

// ─── Golden Item Row ──────────────────────────────────────────────────────────
function GoldenRow({
  item, index, onChange, onRemove
}: {
  item: GoldenItem
  index: number
  onChange: (i: number, f: keyof GoldenItem, v: string) => void
  onRemove: (i: number) => void
}) {
  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-xs font-semibold text-gray-400">#{index + 1}</span>
        <button type="button" onClick={() => onRemove(index)} className="text-gray-300 hover:text-red-400">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
      <input
        type="text"
        placeholder="Question…"
        value={item.question}
        onChange={e => onChange(index, 'question', e.target.value)}
        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <input
        type="text"
        placeholder="Ground truth answer…"
        value={item.ground_truth}
        onChange={e => onChange(index, 'ground_truth', e.target.value)}
        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <input
        type="text"
        placeholder="Document ID (optional — leave blank for all docs)"
        value={item.document_id ?? ''}
        onChange={e => onChange(index, 'document_id', e.target.value)}
        className="w-full text-xs border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-300 text-gray-500"
      />
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
const DEFAULT_CONDITIONS = ['auto', 'similarity', 'hybrid_bm25', 'mmr_cross_encoder']

export default function Evaluate() {
  const [items, setItems] = useState<GoldenItem[]>([
    { question: '', ground_truth: '' }
  ])
  const [conditions, setConditions] = useState<string[]>(DEFAULT_CONDITIONS)
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<EvalRunResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const addItem = () => setItems(v => [...v, { question: '', ground_truth: '' }])
  const removeItem = (i: number) => setItems(v => v.filter((_, idx) => idx !== i))
  const updateItem = (i: number, field: keyof GoldenItem, val: string) =>
    setItems(v => v.map((it, idx) => idx === i ? { ...it, [field]: val } : it))

  const toggleCondition = (c: string) =>
    setConditions(v => v.includes(c) ? v.filter(x => x !== c) : [...v, c])

  const handleRun = async () => {
    const valid = items.filter(it => it.question.trim() && it.ground_truth.trim())
    if (!valid.length) { setError('Add at least one question + ground truth pair.'); return }
    if (!conditions.length) { setError('Select at least one condition.'); return }
    setRunning(true)
    setError(null)
    setResults(null)
    try {
      const r = await evalAPI.run({ golden_items: valid, conditions })
      setResults(r.data.results)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Evaluation failed. Check backend logs.')
    } finally {
      setRunning(false)
    }
  }

  const conditionLabels: Record<string, string> = {
    auto: '✦ Policy Auto',
    similarity: 'Similarity',
    hybrid_bm25: 'Hybrid + BM25',
    mmr_cross_encoder: 'MMR + Cross-Encoder',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">RAGAS Evaluation</h1>
        <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full font-medium">
          Policy vs Manual
        </span>
      </div>

      <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-4 text-sm text-indigo-700 flex gap-2">
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
        <div>
          Build a golden QA dataset, pick which retrieval conditions to compare, then run.
          The system executes each question under every selected condition and scores the results
          using <strong>faithfulness</strong>, <strong>answer relevancy</strong>,
          <strong> context precision</strong>, and <strong>context recall</strong>.
          The <strong>Policy Auto</strong> condition uses the engine's auto-selection for every axis.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Dataset builder ── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Golden Dataset</h2>

          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {items.map((item, i) => (
              <GoldenRow key={i} item={item} index={i} onChange={updateItem} onRemove={removeItem} />
            ))}
          </div>

          <button
            type="button"
            onClick={addItem}
            className="flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
            <Plus className="w-4 h-4" /> Add question
          </button>
        </div>

        {/* ── Conditions selector ── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Conditions to Compare</h2>
          <p className="text-xs text-gray-500">
            Each question will be run once per selected condition. More conditions = longer run time.
          </p>

          <div className="space-y-2">
            {DEFAULT_CONDITIONS.map(c => (
              <label key={c} className={clsx(
                'flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors',
                conditions.includes(c)
                  ? 'border-indigo-300 bg-indigo-50'
                  : 'border-gray-200 hover:border-gray-300'
              )}>
                <input
                  type="checkbox"
                  checked={conditions.includes(c)}
                  onChange={() => toggleCondition(c)}
                  className="accent-indigo-600"
                />
                <div>
                  <p className="text-sm font-medium text-gray-800">{conditionLabels[c]}</p>
                  <p className="text-xs text-gray-400">
                    {c === 'auto' && 'All strategies auto-selected by policy engine'}
                    {c === 'similarity' && 'similarity retrieval, no reranking'}
                    {c === 'hybrid_bm25' && 'hybrid retrieval + BM25 reranking'}
                    {c === 'mmr_cross_encoder' && 'MMR retrieval + cross-encoder reranking'}
                  </p>
                </div>
              </label>
            ))}
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-3 border border-red-200">
              <AlertCircle className="w-4 h-4 shrink-0" /> {error}
            </div>
          )}

          <button
            onClick={handleRun}
            disabled={running}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium text-sm transition-colors disabled:opacity-50"
          >
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running ? 'Running evaluation…' : 'Run Evaluation'}
          </button>
        </div>
      </div>

      {/* ── Results ── */}
      {results && (
        <div className="space-y-4">
          <h2 className="font-semibold text-gray-800 flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-indigo-500" />
            Results
          </h2>

          {/* Winner callout */}
          {(() => {
            const winner = [...results].sort((a, b) => b.overall_score - a.overall_score)[0]
            return (
              <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-sm text-emerald-800">
                <strong>Best overall:</strong>{' '}
                {conditionLabels[winner.condition] ?? winner.condition}
                {' '}— score {Math.round(winner.overall_score * 100)},
                avg {Math.round(winner.avg_tokens)} tokens,
                avg {Math.round(winner.avg_latency_ms)}ms
              </div>
            )
          })()}

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {results.map(r => <ResultCard key={r.condition} r={r} />)}
          </div>

          {/* Token efficiency table */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Condition', 'Overall', 'Faithfulness', 'Relevancy', 'Precision', 'Recall', 'Tokens', 'Latency'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[...results].sort((a, b) => b.overall_score - a.overall_score).map(r => (
                  <tr key={r.condition} className={r.condition === 'auto' ? 'bg-indigo-50' : 'hover:bg-gray-50'}>
                    <td className="px-4 py-2.5 font-medium text-gray-800">
                      {conditionLabels[r.condition] ?? r.condition}
                    </td>
                    <td className="px-4 py-2.5 font-bold text-gray-900">{Math.round(r.overall_score * 100)}%</td>
                    <td className="px-4 py-2.5 text-gray-600">{Math.round(r.faithfulness * 100)}%</td>
                    <td className="px-4 py-2.5 text-gray-600">{Math.round(r.answer_relevancy * 100)}%</td>
                    <td className="px-4 py-2.5 text-gray-600">{Math.round(r.context_precision * 100)}%</td>
                    <td className="px-4 py-2.5 text-gray-600">{r.context_recall != null ? `${Math.round(r.context_recall * 100)}%` : '—'}</td>
                    <td className="px-4 py-2.5 text-gray-600">{Math.round(r.avg_tokens)}</td>
                    <td className="px-4 py-2.5 text-gray-600">{Math.round(r.avg_latency_ms)}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
