import { useState, useRef, useEffect } from 'react'
import { Info, Cpu, Zap } from 'lucide-react'
import { clsx } from 'clsx'

// ─── Tooltip content per strategy ────────────────────────────────────────────
const TOOLTIPS: Record<string, { when: string; tradeoff: string }> = {
  // Chunking
  auto_chunking: {
    when: 'Default — system reads your document and picks the best option.',
    tradeoff: 'Zero configuration needed.'
  },
  fixed: {
    when: 'General prose, short articles, FAQ docs.',
    tradeoff: 'Fast but can split mid-sentence on dense text.'
  },
  recursive: {
    when: 'Code files, nested structured text, technical docs.',
    tradeoff: 'Respects code block boundaries; slightly slower.'
  },
  semantic: {
    when: 'Academic papers, legal contracts, long-form analysis.',
    tradeoff: 'Best quality; requires sentence-transformer pass over the doc.'
  },
  section: {
    when: 'Markdown or numbered-section documents.',
    tradeoff: 'Preserves logical section boundaries exactly.'
  },
  // Embedding
  'BAAI/bge-small-en-v1.5': {
    when: 'Quick ingestion, simple factual docs.',
    tradeoff: '384-dim. Fastest; lowest recall on nuanced queries.'
  },
  'BAAI/bge-base-en-v1.5': {
    when: 'Balanced quality and speed for most documents.',
    tradeoff: '768-dim. Good default for mixed corpora.'
  },
  'BAAI/bge-large-en-v1.5': {
    when: 'High-stakes retrieval: legal, medical, academic.',
    tradeoff: '1024-dim. Best recall; 3× slower to embed.'
  },
  // Retrieval
  similarity: {
    when: 'Simple factual queries against clean documents.',
    tradeoff: 'Fastest. May miss keyword-exact matches.'
  },
  hybrid: {
    when: 'Technical or analytical queries with specific terms.',
    tradeoff: 'Vector + BM25 combined. Best overall recall.'
  },
  mmr: {
    when: 'Broad or comparison queries needing diverse evidence.',
    tradeoff: 'Maximally diverse results; slightly higher latency.'
  },
  // Reranking
  none: {
    when: 'Low-complexity factual queries.',
    tradeoff: 'No extra latency. May return less precise ordering.'
  },
  bm25: {
    when: 'Keyword-heavy or structured queries.',
    tradeoff: 'Lightweight; adds ~10ms.'
  },
  cross_encoder: {
    when: 'Multi-hop or high-complexity queries.',
    tradeoff: 'Deep neural scoring; adds 200–500ms per query.'
  },
  cohere: {
    when: 'Production quality-critical pipelines with Cohere key.',
    tradeoff: 'Best reranking quality; requires API call.'
  },
  // Prompt templates
  factual_qa: {
    when: 'Direct questions with a single correct answer.',
    tradeoff: 'Concise output; low temperature.'
  },
  analysis: {
    when: 'Why/how questions requiring reasoning.',
    tradeoff: 'Longer output with chain-of-thought.'
  },
  comparison: {
    when: 'Compare X vs Y, pros and cons.',
    tradeoff: 'Structured comparative output.'
  },
  creative: {
    when: 'Open-ended generation from document content.',
    tradeoff: 'Higher temperature; less deterministic.'
  },
  code_explanation: {
    when: 'Code-heavy documents and technical questions.',
    tradeoff: 'Explains code constructs step by step.'
  },
  step_by_step: {
    when: 'Procedural or instructional queries.',
    tradeoff: 'Numbered steps; clear reasoning trail.'
  },
  critical_thinking: {
    when: 'Complex questions needing multiple perspectives.',
    tradeoff: 'Longest output; highest reasoning depth.'
  }
}

// ─── Types ───────────────────────────────────────────────────────────────────
interface StrategySelectorProps {
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
  /** When set, shows "Policy picked X" info line */
  policyValue?: string
  disabled?: boolean
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────
function Tooltip({ id }: { id: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const tip = TOOLTIPS[id]
  if (!tip) return null

  return (
    <div className="relative inline-flex items-center ml-1" ref={ref}>
      <button
        type="button"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="text-gray-400 hover:text-indigo-500 transition-colors"
        aria-label={`Tip for ${id}`}
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div className="absolute z-50 bottom-6 left-0 w-64 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-xl">
          <p className="font-semibold mb-1 text-indigo-300">When to use</p>
          <p className="mb-2">{tip.when}</p>
          <p className="font-semibold mb-1 text-yellow-300">Trade-off</p>
          <p>{tip.tradeoff}</p>
          <div className="absolute bottom-[-6px] left-3 w-3 h-3 bg-gray-900 rotate-45" />
        </div>
      )}
    </div>
  )
}

// ─── AutoBadge ───────────────────────────────────────────────────────────────
function AutoBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-100 text-indigo-700 border border-indigo-200">
      <Cpu className="w-2.5 h-2.5" />
      AUTO
    </span>
  )
}

// ─── PolicyHint ───────────────────────────────────────────────────────────────
function PolicyHint({ value }: { value: string }) {
  const displayName = value.includes('/') ? value.split('/').pop()! : value
  return (
    <span className="text-[11px] text-indigo-600 flex items-center gap-1 mt-0.5">
      <Zap className="w-3 h-3" />
      Policy would pick: <strong>{displayName}</strong>
    </span>
  )
}

// ─── StrategySelector ────────────────────────────────────────────────────────
export default function StrategySelector({
  label,
  value,
  options,
  onChange,
  policyValue,
  disabled = false
}: StrategySelectorProps) {
  const isAuto = value === 'auto'
  const selectedTip = isAuto ? null : TOOLTIPS[value]

  return (
    <div className="space-y-1">
      <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide flex items-center gap-1">
        {label}
      </label>

      <div className="flex items-center gap-2">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={clsx(
            'flex-1 text-sm border rounded-lg px-3 py-1.5 bg-white',
            'focus:outline-none focus:ring-2 focus:ring-indigo-400',
            isAuto
              ? 'border-indigo-300 text-indigo-700 font-medium'
              : 'border-gray-300 text-gray-800',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt === 'auto' ? '✦ Auto (Recommended)' : opt.includes('/') ? opt.split('/').pop()! : opt}
            </option>
          ))}
        </select>

        {isAuto && <AutoBadge />}
        {!isAuto && selectedTip && <Tooltip id={value} />}
      </div>

      {isAuto && policyValue && policyValue !== 'auto' && (
        <PolicyHint value={policyValue} />
      )}
      {!isAuto && selectedTip && (
        <p className="text-[11px] text-gray-500 leading-tight">{selectedTip.when}</p>
      )}
    </div>
  )
}
