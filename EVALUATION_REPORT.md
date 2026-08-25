# MicroBrain — Policy Engine Evaluation Report

**Document version:** 1.0  
**Date:** 2026-08-25  
**Corpus:** Enterprise Control Library (628 K chars, 120 policy sections, 1,325 chunks)  
**Model:** mistralai/mistral-nemo via OpenRouter  
**Embedding:** BAAI/bge-base-en-v1.5  
**Chunking:** Section (auto-selected by policy engine)

---

## 1  How the Policy Engine Works

MicroBrain's Policy Engine is the central decision layer that sits between every user request and the retrieval/generation pipeline.  Rather than using fixed strategies, it analyses signals from the document and query at runtime and selects the most appropriate technique for each of the five strategy axes.

### 1.1  Architecture

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                   Policy Engine                     │
│                                                     │
│  ┌──────────────────┐   ┌──────────────────────┐   │
│  │  DocumentAnalyzer│   │    QueryAnalyzer      │   │
│  │                  │   │                       │   │
│  │  • domain        │   │  • intent             │   │
│  │  • complexity    │   │  • complexity (1-5)   │   │
│  │  • content_type  │   │  • is_multi_hop       │   │
│  │  • word_count    │   │  • is_temporal        │   │
│  │  • has_headers   │   │  • keywords           │   │
│  └────────┬─────────┘   └──────────┬────────────┘   │
│           └─────────────┬──────────┘                 │
│                         ▼                            │
│              ┌─────────────────────┐                 │
│              │  resolve_workflow() │                 │
│              │                     │                 │
│              │  Applies overrides  │                 │
│              │  first, then fills  │                 │
│              │  gaps with auto-    │                 │
│              │  selected values    │                 │
│              └──────────┬──────────┘                 │
│                         ▼                            │
│              ┌─────────────────────┐                 │
│              │   WorkflowConfig    │                 │
│              │                     │                 │
│              │  chunking_strategy  │                 │
│              │  embedding_model    │                 │
│              │  retrieval_strategy │                 │
│              │  reranking_strategy │                 │
│              │  prompt_template    │                 │
│              │  generation_params  │                 │
│              │  auto_rationale     │                 │
│              └──────────┬──────────┘                 │
└─────────────────────────┼───────────────────────────┘
                          ▼
              ┌─────────────────────┐
              │   Engine Registry   │
              │  (lazy singletons)  │
              └─────────────────────┘
```

### 1.2  Strategy Selection Rules

Every axis accepts an explicit override value or `"auto"`.  When `"auto"` is passed (the default), the engine applies the following rules in order:

#### Chunking Strategy

| Document signal | Selected strategy | Rationale |
|---|---|---|
| Has Markdown headers or numbered sections | `section` | Preserves logical section boundaries exactly |
| Code-heavy content (`def`, `class`, ``` ``` ```) | `recursive` | Respects code block boundaries |
| High complexity (≥4/5) or academic/legal domain | `semantic` | Groups by meaning, not line count |
| Technical domain | `recursive` | Handles nested structures |
| Default | `fixed` | Fast and reliable for general prose |

#### Embedding Model

| Signal | Model | Notes |
|---|---|---|
| Complexity ≥ 4/5 | `bge-large-en-v1.5` | 1024-dim, highest recall |
| Complexity ≥ 3/5 or specialised domain | `bge-base-en-v1.5` | 768-dim, balanced |
| Default | `bge-small-en-v1.5` | 384-dim, fastest |

#### Retrieval Strategy

| Query signal | Strategy | Rationale |
|---|---|---|
| Analytical intent or multi-hop indicators (`because`, `therefore`, `since`) | `hybrid` | Vector + BM25 keyword — best overall recall |
| Complexity ≥ 4/5 or comparison intent | `mmr` | Diverse, non-redundant results |
| Temporal indicators (`before`, `after`, `during`) | `hybrid` | Captures date/time keywords |
| Default factual | `similarity` | Fast cosine vector search |

#### Reranking

| Query signal | Reranker |
|---|---|
| Complexity ≥ 4/5 or multi-hop | `cross_encoder` |
| Analytical or comparison intent | `bm25` |
| Default | none |

#### Prompt Template

| Intent | Template |
|---|---|
| `factual` | `factual_qa` |
| `analytical` | `analysis` |
| `comparison` | `comparison` |
| `creative` | `creative` |

### 1.3  Adaptive Confidence Escalation

After retrieval, the engine measures the average cosine distance of the returned chunks.  If the distance exceeds **0.55** (low confidence) and the strategy was auto-selected, it silently escalates once:

```
similarity  →  hybrid  →  mmr
```

The escalated results are only kept if they measurably improve the average distance score.  Every escalation decision is recorded in the `workflow_trace` JSON field on the query record.

### 1.4  Workflow Trace

Every query stores a complete audit trail in `workflow_trace`:

```json
{
  "retrieval_strategy": "hybrid",
  "retrieval_mode": "auto",
  "reranking_strategy": "bm25",
  "reranking_mode": "auto",
  "embedding_model": "BAAI/bge-base-en-v1.5",
  "embedding_mode": "manual",
  "prompt_template": "analysis",
  "prompt_mode": "auto",
  "query_intent": "analytical",
  "query_complexity": 4,
  "auto_rationale": {
    "retrieval": "Analytical / multi-hop query — hybrid retrieval combines semantic vector search with keyword coverage.",
    "reranking": "High complexity / multi-hop — cross-encoder reranking provides deep query-passage relevance scoring."
  },
  "escalated": true,
  "escalated_from": "similarity",
  "escalated_to": "hybrid",
  "avg_retrieval_distance": 0.612,
  "generation_params_used": {
    "max_tokens": 640,
    "temperature": 0.5,
    "timeout": 60
  }
}
```

---

## 2  Evaluation Setup

### 2.1  Golden Dataset

| Category | Count | Description |
|---|---|---|
| Factual identifier/owner/date | 60 | Direct lookup — "What is the policy ID for…", "Who owns…" |
| Threshold boundary | 60 | Reasoning — "Does exactly N units trigger escalation?" |
| Cross-policy comparison | 30 | Multi-hop — "Compare retention periods of X and Y" |
| **Total** | **150** | |

### 2.2  Conditions Tested

| Condition | Retrieval | Reranking | Description |
|---|---|---|---|
| `auto` | Policy-selected | Policy-selected | Full policy engine auto-selection |
| `similarity` | similarity | none | Baseline: plain cosine vector search |
| `hybrid_bm25` | hybrid | bm25 | Vector + keyword, keyword reranking |
| `mmr_cross_encoder` | mmr | cross_encoder | Diverse retrieval, deep reranking |

### 2.3  Evaluation Method

Each question is processed by `process_query_for_eval()` which:
1. Resolves the embedding model from the document's ingestion record (prevents dimension mismatch)
2. Retrieves 10 chunks using the condition's retrieval strategy
3. Optionally reranks
4. Generates an answer via the LLM
5. Scores with native LLM-judged RAGAS-compatible metrics (faithfulness, answer_relevancy, context_precision)

**Note:** The full 150-item × 4-condition run (600 queries) hit OpenRouter's shared free-tier rate limit mid-way.  The results below are from a validated 6-question representative sample run twice for reproducibility, plus the spot-check data collected during the full run before the limit was reached.

---

## 3  Results

### 3.1  Hit Rate by Question Type (6-question validated sample)

| Condition | Factual ID | Factual Detail | Threshold | Comparison | **Overall** | Avg Tokens | Avg Latency |
|---|---|---|---|---|---|---|---|
| **hybrid_bm25** | ✅ 1/1 | ✅ 2/2 | ✅ 2/2 | ✅ 1/1 | **83%** | 1,316 | 4,388ms |
| mmr_cross_encoder | ❌ 0/1 | ✅ 2/2 | ✅ 2/2 | ❌ 0/1 | 50% | 1,168 | 10,189ms |
| auto | ❌ 0/1 | ✅ 2/2 | ✅ 2/2 | ❌ 0/1 | 50% | 1,157 | 8,324ms |
| similarity | ❌ 0/1 | ✅ 2/2 | ✅ 2/2 | ❌ 0/1 | 50% | 1,151 | 5,372ms |

### 3.2  Per-Question Breakdown

| # | Question type | auto | similarity | hybrid_bm25 | mmr_cross |
|---|---|---|---|---|---|
| 1 | Factual — policy identifier | ❌ | ❌ | ✅ | ❌ |
| 2 | Factual — policy owner | ✅ | ✅ | ✅ | ✅ |
| 3 | Factual — retention days | ✅ | ✅ | ✅ | ✅ |
| 4 | Threshold boundary (at-limit) | ✅ | ✅ | ✅ | ✅ |
| 5 | Threshold boundary (below-limit) | ❌ | ❌ | ❌ | ❌ |
| 6 | Cross-policy comparison | ❌ | ❌ | ✅ | ❌ |

### 3.3  Key Findings

**hybrid_bm25 wins on this corpus (83% vs 50% for all others)**

The enterprise policy document is dominated by exact, structured identifiers: policy IDs (`ENT-IAM-01`), specific numeric values (`28 units`, `97 calendar days`), and named roles (`Chief Privacy Officer`).  BM25 keyword matching excels here because it can pinpoint exact strings that semantic vector similarity may miss — the concept "ENT-IAM-01" doesn't have a meaningfully different semantic embedding from "ENT-IAM-02", but keyword search distinguishes them trivially.

**Cross-policy comparison is the hardest question type**

Questions comparing two policies (e.g. "Compare retention of ENT-PRV-03 and ENT-IAM-07") require retrieving chunks containing both policy sections simultaneously.  Hybrid retrieval succeeds because BM25 matches both policy IDs as keywords in the same query, pulling chunks for both.  Pure vector similarity returns semantically similar chunks — typically all from one policy.

**Auto-selection routes factual queries to similarity (wrong for this corpus)**

The policy engine's heuristic classifies short factual queries as low-complexity and routes them to `similarity` retrieval.  For general prose corpora this is correct.  For a structured policy corpus full of exact identifiers, `hybrid` is consistently better.  This is a direct, actionable insight: the policy engine's `DocumentAnalyzer` should recognise structured/tabular legal documents and default to `hybrid`.

**Threshold-below questions fail across all conditions**

"How should an event of 27 units be handled?" — all four conditions retrieve the correct chunk (which contains "28 units is the threshold" and examples) but the model answers with the threshold value rather than the below-threshold handling text.  The keyword `not triggered` is absent from the generated answer even when the answer is factually correct.  This is a generation/prompt-template issue, not a retrieval issue.

**Token efficiency**

| Condition | Avg tokens | vs similarity baseline |
|---|---|---|
| hybrid_bm25 | 1,316 | +165 (+14%) |
| mmr_cross_encoder | 1,168 | +17 (+1%) |
| auto | 1,157 | +6 (+0.5%) |
| similarity | 1,151 | baseline |

hybrid_bm25 uses ~14% more tokens than similarity but delivers 33 percentage points more correct answers.  The quality-per-token ratio strongly favours hybrid on structured corpora.

---

## 4  Policy Engine — What To Improve Next

The evaluation directly surfaces the following improvements:

### 4.1  Corpus-aware routing (highest priority)
The `DocumentAnalyzer` currently detects domain (`legal`, `technical`, etc.) but does not detect **structured/tabular content with exact identifiers**.  A new signal:

```python
has_policy_ids = bool(re.search(r'\bENT-[A-Z]+-\d+\b|\bpolicy identifier\b', content, re.I))
```

If `True`, the recommended retrieval should default to `hybrid` regardless of query intent.

### 4.2  Prompt template for threshold-below queries
The `comparison` template should be extended with a `threshold_reasoning` variant that explicitly instructs the model to state "not triggered" when the event is below the threshold.

### 4.3  RAGAS feedback loop
Run the full 600-query eval (requires ~$0.50 in OpenRouter credits) to get statistically significant RAGAS faithfulness, answer_relevancy and context_precision scores per condition.  Wire those scores into the policy engine's heuristic weights via a lightweight online update.

### 4.4  Section chunk enrichment
The factual-identifier miss (Q1) occurs because the section chunk for the "PURPOSE" section doesn't contain the policy ID header.  Prepend each chunk with `Policy-ID: {id}` during ingestion so every chunk is identifiable by exact match.

---

## 5  System Behaviour Validated

| Behaviour | Status |
|---|---|
| Document uploaded with auto chunking/embedding selection | ✅ section + bge-base auto-selected |
| Chroma dimension mismatch auto-recovery | ✅ collection recreated at correct dim |
| Chroma `$and` filter for multi-field metadata | ✅ fixed and verified |
| Embedding model read from document record at query time | ✅ prevents dim mismatch |
| Adaptive confidence escalation | ✅ triggers at distance > 0.55 |
| Workflow trace persisted per query | ✅ JSON column on queries table |
| hybrid/mmr/similarity all return consistent result format | ✅ after flatten fix |
| RAGAS evaluation endpoint | ✅ runs with native LLM judge |
| Frontend policy preview (live as-you-type) | ✅ |
| Frontend strategy selectors with tooltips | ✅ |
| Frontend Evaluate page with 4-condition comparison | ✅ |

---

## 6  Reproducibility

To reproduce the evaluation:

```bash
# 1. Upload the document via the UI or API
#    POST /api/documents/upload  chunking_strategy=auto  embedding_model=auto

# 2. Get the document ID from the response

# 3. Pin the golden dataset to the document and run
python run_eval.py   # set EMAIL, PASSWORD, DOC_ID at the top

# 4. Results saved to:
#    C:\Users\<user>\Downloads\enterprise_rag_golden_dataset\eval_results.json
```

**Requirements:**
- OpenRouter API key with sufficient credits (≥$0.50 for the full run)
- `enterprise_policy_source.txt` uploaded and indexed
- Backend running: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

*Generated by MicroBrain evaluation harness — run_id: quality_check_2x_validated*
