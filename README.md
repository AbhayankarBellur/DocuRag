# MicroBrain

**Multi-user Retrieval-Augmented Generation platform with an intelligent policy engine that auto-selects the optimal chunking, embedding, and retrieval strategy for every document and query.**

---

## Overview

MicroBrain is a self-hosted RAG API built with FastAPI, ChromaDB, and sentence-transformers. It exposes a full document ingestion → retrieval → generation pipeline through a REST API consumed by a Next.js frontend.

The core differentiator is the **Policy Engine** — a rule-based routing layer that analyses document structure and query intent at runtime and selects the most appropriate strategy across all five pipeline axes (chunking, embedding, retrieval, reranking, prompt template) without any user intervention. Every axis also accepts explicit override values, so manual control is always available.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Next.js Frontend                    │
└──────────────────────────┬──────────────────────────────┘
                           │ REST
┌──────────────────────────▼──────────────────────────────┐
│                     FastAPI Backend                      │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │  /documents  │   │   /queries   │   │   /policy   │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬──────┘  │
│         │                  │                  │          │
│  ┌──────▼──────────────────▼──────────────────▼──────┐  │
│  │                   Policy Engine                    │  │
│  │   DocumentAnalyzer  ──►  WorkflowConfig            │  │
│  │   QueryAnalyzer     ──►  (5 resolved strategies)  │  │
│  └──────────────────────────┬──────────────────────── ┘  │
│                             │                            │
│  ┌──────────────────────────▼──────────────────────────┐ │
│  │                   Engine Registry                    │ │
│  │  Chunking │ Embedding │ VectorStore │ Retrieval      │ │
│  │  Reranking │ Generation                              │ │
│  └──────────────────────────────────────────────────── ┘ │
└─────────────────────────────────────────────────────────┘
```

### Request flow — document ingestion

```
Upload file
  → IngestionEngine (text extraction)
  → PolicyEngine.resolve_workflow(document_content, overrides)
  → EngineRegistry.get_chunking(strategy)   → chunk text
  → EngineRegistry.get_embedding(model)     → embed chunks
  → EngineRegistry.get_vector_store("chroma") → persist
  → DB record updated with resolved strategy names
```

### Request flow — query

```
POST /api/queries/
  → PolicyEngine.resolve_workflow(query, overrides)
  → EngineRegistry.get_embedding(model)     → embed query
  → EngineRegistry.get_retrieval(strategy)  → fetch chunks
  → EngineRegistry.get_reranking(strategy)  → optional rerank
  → TemplateManager.get_template(...)       → build prompt
  → GenerationEngine.generate_with_context  → answer
  → DB record with resolved strategies + metrics
```

---

## Policy Engine

### Auto-selection signals

| Signal | Source | Used for |
|--------|--------|----------|
| Has section headers | Document structure | → section chunking |
| Code blocks present | Document structure | → recursive chunking |
| Domain (legal/tech/academic) | Keyword density | → chunking + embedding size |
| Word count / complexity | Document stats | → embedding model size |
| Query intent (factual/analytical/comparison/creative) | Pattern matching | → retrieval + prompt template |
| Multi-hop indicators (because/therefore/since) | Query signals | → hybrid retrieval + cross-encoder rerank |
| Temporal indicators (before/after/during) | Query signals | → hybrid retrieval |
| Query complexity score (1–5) | Word count + indicators | → reranking decision |

### Decision table

| Condition | Chunking | Embedding | Retrieval | Reranking |
|-----------|----------|-----------|-----------|-----------|
| Headers / numbered sections | `section` | — | — | — |
| Code-heavy content | `recursive` | — | — | — |
| High complexity or academic/legal domain | `semantic` | `bge-large` | — | — |
| Technical domain | `recursive` | `bge-base` | `hybrid` | — |
| Analytical / multi-hop query | — | — | `hybrid` | `bm25` |
| Complex / comparison query | — | — | `mmr` | `cross_encoder` |
| Default | `fixed` | `bge-small` | `similarity` | none |

### Manual override

Every strategy field accepts an explicit value alongside `"auto"`. Pass any subset — the rest are auto-selected:

```json
POST /api/queries/
{
  "question": "Compare the two approaches",
  "retrieval_strategy": "mmr",
  "reranking_strategy": "auto",
  "embedding_model": "auto"
}
```

---

## API Reference

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents/upload` | Upload document. `chunking_strategy` and `embedding_model` accept `"auto"` or explicit values |
| `GET` | `/api/documents/list` | List user's documents |
| `GET` | `/api/documents/{id}` | Get document metadata |
| `DELETE` | `/api/documents/{id}` | Delete document and its vectors |
| `PUT` | `/api/documents/{id}` | Update document metadata |

### Queries

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/queries/` | Execute a query (all strategy fields optional, default `"auto"`) |
| `GET` | `/api/queries/history` | Query history for current user |
| `GET` | `/api/queries/{id}` | Get specific query result |
| `POST` | `/api/batch` | Submit a batch of queries |

### Policy

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/policy/options` | All valid strategy values per axis (with `"auto"` prepended) |
| `POST` | `/api/policy/workflow-preview` | Resolve and return a WorkflowConfig without executing anything |

### Auth / Admin / Folders

Standard JWT auth (`/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`), admin endpoints, and folder CRUD at `/api/folders`.

Interactive docs available at `/docs` when the server is running.

---

## Supported Strategies

### Chunking
| Value | When to use |
|-------|-------------|
| `fixed` | Default, uniform size, fast |
| `recursive` | Code or nested structured text |
| `semantic` | High-complexity prose, academic/legal |
| `section` | Documents with Markdown or numbered headers |

### Embedding models
| Value | Notes |
|-------|-------|
| `BAAI/bge-small-en-v1.5` | Default, fastest, 384-dim |
| `BAAI/bge-base-en-v1.5` | Better quality, 768-dim |
| `BAAI/bge-large-en-v1.5` | Best quality, 1024-dim, slower |

### Retrieval
| Value | When to use |
|-------|-------------|
| `similarity` | Default cosine vector search |
| `hybrid` | Vector + BM25 keyword, best for technical/analytical queries |
| `mmr` | Maximal Marginal Relevance — diverse, non-redundant results |

### Reranking
| Value | When to use |
|-------|-------------|
| `bm25` | Lightweight keyword reranking |
| `cross_encoder` | Deep neural reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`) |
| `cohere` | Cohere Rerank API (requires `COHERE_API_KEY`) |
| `none` | Disabled |

### Generation providers
| Value | Notes |
|-------|-------|
| `openrouter` | Default. Free tier available (`nvidia/nemotron-3-super-120b-a12b:free`) |
| `openai` | Requires billing credits |
| `huggingface` | Requires `HUGGINGFACE_API_KEY` and network access to `api-inference.huggingface.co` |

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (frontend)

### Backend

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate      # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY at minimum

# Start server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment variables (`.env`)

```env
# Required for generation
GENERATION_PROVIDER=openrouter        # openrouter | openai | huggingface
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free

# Optional — OpenAI (requires billing credits)
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# Optional — Cohere reranking
COHERE_API_KEY=...

# App secrets
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite+aiosqlite:///./microbrain.db
```

---

## Project Structure

```
app/
├── api/
│   ├── auth.py            # JWT authentication
│   ├── documents.py       # Document upload/management
│   ├── queries.py         # Query execution
│   ├── policy.py          # Policy options + workflow preview  ← new
│   ├── folders.py
│   ├── batch.py
│   └── admin.py
├── engines/
│   ├── registry.py        # Lazy singleton engine registry     ← new
│   ├── chunking/          # fixed | recursive | semantic | section
│   ├── embedding/         # BGE small/base/large
│   ├── generation/
│   │   ├── hf_inference.py
│   │   ├── openai_inference.py                                 ← new
│   │   └── openrouter_inference.py                             ← new
│   ├── retrieval/         # similarity | hybrid | mmr
│   ├── reranking/         # bm25 | cross_encoder | cohere
│   ├── storage/           # chroma | faiss | qdrant
│   ├── prompting/
│   ├── evaluation/        # deepeval | ragas stubs
│   └── ingestion.py
├── policy/
│   ├── models.py          # WorkflowConfig + strategy enums    ← new
│   ├── engine.py          # resolve_workflow()                 ← updated
│   ├── document_analyzer.py                                    ← updated
│   ├── query_analyzer.py                                       ← updated
│   └── workflow_selector.py
├── services/
│   ├── document_service.py                                     ← updated
│   └── query_service.py                                        ← updated
├── models/
│   ├── document.py
│   ├── query.py                                                ← updated
│   └── user.py
└── utils/
    └── config.py                                               ← updated
```

---

## Potential Improvements

### Retrieval quality

1. **RAPTOR-style hierarchical indexing** — cluster chunks into summaries at multiple abstraction levels so both detail and theme queries are answered well.
2. **HyDE (Hypothetical Document Embeddings)** — generate a hypothetical answer before retrieval to close the query/document representation gap.
3. **Query expansion / RAG-Fusion** — generate N rephrased queries, retrieve independently, merge with Reciprocal Rank Fusion.
4. **Late-interaction retrieval (ColBERT-style)** — token-level MaxSim scoring instead of single-vector similarity.
5. **Contextual chunk enrichment** — prepend document title + section heading to each chunk before embedding, reducing context loss.

### Policy engine

6. **Feedback loop** — record user ratings per query, use them to adjust strategy weights over time (lightweight online learning).
7. **Per-domain strategy profiles** — allow configuring a fixed strategy profile per detected domain instead of relying purely on heuristics.
8. **Cost-aware routing** — factor token cost and latency into strategy selection (e.g. prefer BM25 reranking over cross-encoder when p95 latency exceeds threshold).
9. **Confidence scoring** — when retrieved chunks have low similarity scores, automatically widen retrieval or switch strategy rather than returning a low-confidence answer.

### Evaluation (RAGAS integration)

10. **Automated RAGAS benchmarking** — the `app/engines/evaluation/ragas_eval.py` stub is already in place. Wire it to run on a fixed golden QA dataset after each query batch and record:
    - `faithfulness` — is the answer grounded in the retrieved context?
    - `answer_relevancy` — does the answer address the question?
    - `context_precision` / `context_recall` — quality of the retrieved chunks
11. **Policy vs. manual comparison harness** — run the same input set twice (once with `retrieval_strategy="auto"`, once with each explicit strategy) and compare RAGAS scores + token consumption. This directly validates whether the policy engine's selections outperform naive defaults.
12. **Token efficiency metric** — log `prompt_tokens` and `completion_tokens` per query (already stored for OpenAI/OpenRouter). Add a dashboard metric for `quality_per_token = answer_relevancy / total_tokens`.

### Infrastructure

13. **Async embedding** — move `embed_batch` calls to a background task queue (Celery is already wired) so large document uploads don't block the request thread.
14. **Streaming generation** — use SSE to stream token-by-token generation output to the frontend, dramatically improving perceived latency.
15. **PostgreSQL migration** — SQLite works for development but is a write bottleneck under concurrent users. Alembic migrations are scaffolded; switching is a one-line `DATABASE_URL` change.
16. **Vector store per user / collection sharding** — currently all users share one Chroma collection filtered by metadata. Separate collections per user would improve query isolation and deletion performance.
17. **Retry + circuit-breaker on generation** — the current fallback is silent. Add tenacity-based retry with exponential backoff and a dead-letter queue for failed generations.

### Document processing

18. **OCR support** — add Tesseract/easyOCR for scanned PDFs that contain no extractable text.
19. **Table-aware chunking** — detect and preserve table boundaries instead of splitting mid-row.
20. **Multi-language embedding** — swap to `BAAI/bge-m3` for corpora that mix languages.

---

## RAGAS Evaluation Plan

The goal is to objectively compare **policy auto-selection** vs **fixed manual strategies** on the same inputs.

### Dataset
Build a golden set of 50–100 QA pairs across document types (technical docs, legal text, academic papers). Each pair:
```json
{
  "question": "...",
  "ground_truth": "...",
  "document_id": "..."
}
```

### Metrics to collect per run
| Metric | Source | Notes |
|--------|--------|-------|
| `faithfulness` | RAGAS | Answer supported by retrieved context |
| `answer_relevancy` | RAGAS | Answer addresses the question |
| `context_precision` | RAGAS | Fraction of retrieved chunks actually useful |
| `context_recall` | RAGAS | Relevant chunks that were retrieved |
| `total_tokens` | DB `token_usage` | Cost proxy |
| `total_time_ms` | DB `total_time` | Latency |

### Experimental conditions
| Run | Config |
|-----|--------|
| A — Policy auto | `retrieval_strategy="auto"`, all others auto |
| B — Similarity baseline | `retrieval_strategy="similarity"`, no reranking |
| C — Hybrid + BM25 rerank | `retrieval_strategy="hybrid"`, `reranking_strategy="bm25"` |
| D — MMR + cross-encoder | `retrieval_strategy="mmr"`, `reranking_strategy="cross_encoder"` |

### Implementation path
1. Activate `app/engines/evaluation/ragas_eval.py` — the stub is already present.
2. Add a `POST /api/admin/evaluate` endpoint that accepts a golden dataset and runs all four conditions.
3. Return a comparison table with mean scores and token costs per condition.
4. Use this to tune the policy engine's decision thresholds.

---

## License

MIT
