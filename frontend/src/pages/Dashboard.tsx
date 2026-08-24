import { useEffect, useState } from 'react'
import { documentAPI, queryAPI } from '../services/api'
import { FileText, MessageSquare, Clock, Hash, Cpu, Zap, BarChart2 } from 'lucide-react'

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ icon, label, value, sub }: {
  icon: React.ReactNode; label: string; value: string | number; sub?: string
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 flex items-center gap-4">
      <div className="p-3 bg-indigo-50 rounded-xl text-indigo-500">{icon}</div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

// ─── Mini bar chart (pure CSS) ────────────────────────────────────────────────
function MiniBar({ label, count, total, color }: {
  label: string; count: number; total: number; color: string
}) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-24 text-gray-600 text-xs truncate capitalize">{label}</span>
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-xs text-gray-400">{count}</span>
    </div>
  )
}

// ─── Strategy distribution block ──────────────────────────────────────────────
function StrategyDistribution({ queries }: { queries: any[] }) {
  if (!queries.length) return null

  const count = (field: string) => {
    const map: Record<string, number> = {}
    for (const q of queries) {
      const v = q[field] ?? 'unknown'
      map[v] = (map[v] ?? 0) + 1
    }
    return map
  }

  const retrieval = count('retrieval_strategy')
  const reranking = count('reranking_strategy')
  const total = queries.length

  const barColors = ['bg-indigo-400', 'bg-violet-400', 'bg-emerald-400', 'bg-amber-400', 'bg-rose-400']

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-5">
      <h3 className="font-semibold text-gray-800 flex items-center gap-2">
        <BarChart2 className="w-4 h-4 text-indigo-400" />
        Strategy Distribution
      </h3>

      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Retrieval</p>
        <div className="space-y-1.5">
          {Object.entries(retrieval).map(([k, v], i) => (
            <MiniBar key={k} label={k} count={v} total={total} color={barColors[i % barColors.length]} />
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Reranking</p>
        <div className="space-y-1.5">
          {Object.entries(reranking).map(([k, v], i) => (
            <MiniBar key={k} label={k ?? 'none'} count={v} total={total} color={barColors[i % barColors.length]} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Policy Efficiency block ──────────────────────────────────────────────────
function PolicyEfficiency({ queries }: { queries: any[] }) {
  const withMetrics = queries.filter(q => q.total_time != null && q.token_usage != null)
  if (!withMetrics.length) return null

  const avgLatency = Math.round(withMetrics.reduce((s, q) => s + q.total_time, 0) / withMetrics.length)
  const avgTokens = Math.round(withMetrics.reduce((s, q) => s + q.token_usage, 0) / withMetrics.length)
  const avgRetrieval = Math.round(
    withMetrics.filter(q => q.retrieval_time).reduce((s, q) => s + q.retrieval_time, 0) /
    Math.max(withMetrics.filter(q => q.retrieval_time).length, 1)
  )

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
      <h3 className="font-semibold text-gray-800 flex items-center gap-2">
        <Zap className="w-4 h-4 text-emerald-400" />
        Policy Efficiency
        <span className="text-xs text-gray-400 font-normal">last {withMetrics.length} queries</span>
      </h3>
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Avg Latency', value: `${avgLatency}ms`, icon: <Clock className="w-4 h-4" /> },
          { label: 'Avg Tokens', value: avgTokens, icon: <Hash className="w-4 h-4" /> },
          { label: 'Avg Retrieval', value: `${avgRetrieval}ms`, icon: <Cpu className="w-4 h-4" /> },
        ].map(m => (
          <div key={m.label} className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="flex justify-center text-indigo-400 mb-1">{m.icon}</div>
            <p className="text-lg font-bold text-gray-800">{m.value}</p>
            <p className="text-[10px] text-gray-400">{m.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const [docs, setDocs] = useState<any[]>([])
  const [queries, setQueries] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([documentAPI.list(0, 100), queryAPI.history(0, 100)])
      .then(([d, q]) => { setDocs(d.data); setQueries(q.data) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-gray-400">Loading…</div>

  const recent5docs = docs.slice(0, 5)
  const recent5q = queries.slice(0, 5)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<FileText className="w-5 h-5" />} label="Documents" value={docs.length} />
        <StatCard icon={<MessageSquare className="w-5 h-5" />} label="Queries" value={queries.length} />
        <StatCard
          icon={<Clock className="w-5 h-5" />}
          label="Avg Latency"
          value={queries.filter(q => q.total_time).length
            ? `${Math.round(queries.filter(q => q.total_time).reduce((s, q) => s + q.total_time, 0) / queries.filter(q => q.total_time).length)}ms`
            : '—'}
        />
        <StatCard
          icon={<Hash className="w-5 h-5" />}
          label="Avg Tokens"
          value={queries.filter(q => q.token_usage).length
            ? Math.round(queries.filter(q => q.token_usage).reduce((s, q) => s + q.token_usage, 0) / queries.filter(q => q.token_usage).length)
            : '—'}
        />
      </div>

      {/* ── Middle row ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <PolicyEfficiency queries={queries} />
        <StrategyDistribution queries={queries} />
      </div>

      {/* ── Recent activity ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" /> Recent Documents
          </h2>
          {recent5docs.length === 0
            ? <p className="text-gray-400 text-sm">No documents yet.</p>
            : <ul className="space-y-2">
              {recent5docs.map(d => (
                <li key={d.id} className="flex items-center gap-2 text-sm">
                  <FileText className="w-3.5 h-3.5 text-gray-300 shrink-0" />
                  <span className="truncate text-gray-700">{d.title}</span>
                  {d.domain && (
                    <span className="ml-auto text-[10px] text-gray-400 shrink-0">{d.domain}</span>
                  )}
                </li>
              ))}
            </ul>}
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-gray-400" /> Recent Queries
          </h2>
          {recent5q.length === 0
            ? <p className="text-gray-400 text-sm">No queries yet.</p>
            : <ul className="space-y-2">
              {recent5q.map(q => (
                <li key={q.id} className="space-y-0.5">
                  <p className="text-sm text-gray-700 truncate">{q.question}</p>
                  <p className="text-[11px] text-gray-400 flex gap-2">
                    {q.retrieval_strategy && <span>{q.retrieval_strategy}</span>}
                    {q.total_time && <span>{q.total_time}ms</span>}
                    {q.token_usage && <span>{q.token_usage} tok</span>}
                  </p>
                </li>
              ))}
            </ul>}
        </div>
      </div>
    </div>
  )
}
