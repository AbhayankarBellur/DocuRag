"""Query Service"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.registry import get_registry
from app.models.query import (
    BatchQueryCreate,
    BatchQueryResponse,
    Query,
    QueryCreate,
    QueryResponse,
    QueryStatus,
)
from app.policy.engine import PolicyEngine
from app.policy.models import WorkflowConfig
from app.utils.config import settings

from app.engines.generation.hf_inference import HFInference
from app.engines.generation.openai_inference import OpenAIInference
from app.engines.generation.openrouter_inference import OpenRouterInference
from app.engines.prompting.template_manager import (
    MODEL_CONFIGS,
    PromptType,
    ReasoningLevel,
    TemplateManager,
)

# ── Confidence thresholds ────────────────────────────────────────────────────
# If the best retrieved chunk's similarity distance is ABOVE this value
# (i.e. low cosine similarity, since Chroma returns distance not similarity),
# we escalate the retrieval strategy once before generating.
_LOW_CONFIDENCE_DISTANCE_THRESHOLD = 0.55   # 0 = identical, 1 = orthogonal
_ESCALATION_MAP = {
    "similarity": "hybrid",
    "hybrid": "mmr",
    "mmr": "mmr",   # already at top — no further escalation
}


def _build_generator():
    """Return the configured generation engine based on GENERATION_PROVIDER."""
    provider = (settings.generation_provider or "huggingface").lower()
    if provider == "openrouter" and settings.openrouter_api_key:
        print(f"INFO: Using OpenRouter generator — model={settings.openrouter_model}", flush=True)
        return OpenRouterInference(api_key=settings.openrouter_api_key, model=settings.openrouter_model)
    if provider == "openai" and settings.openai_api_key:
        print(f"INFO: Using OpenAI generator — model={settings.openai_model}", flush=True)
        return OpenAIInference(api_key=settings.openai_api_key, model=settings.openai_model)
    print("INFO: Using HuggingFace generator", flush=True)
    return HFInference()


def _avg_distance(results: list) -> float:
    """Return average similarity distance of retrieved results (lower = more relevant)."""
    scores = [r.get("score") for r in results if r.get("score") is not None]
    return sum(scores) / len(scores) if scores else 0.0


class QueryService:
    """Query processing service with policy-driven strategy selection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._policy = PolicyEngine()
        self._registry = get_registry()
        self._generator = _build_generator()
        self._template_manager = TemplateManager()

    # ------------------------------------------------------------------
    # Embedding model resolver — always matches the ingestion model
    # ------------------------------------------------------------------

    async def _resolve_embedding_model(
        self,
        document_id: Optional[str],
        user_id: str,
        override: Optional[str],
    ) -> str:
        """
        Return the embedding model to use for a query.

        Priority:
        1. Explicit override from the caller (non-auto value)
        2. Model recorded on the document at ingestion time
        3. Policy engine default (bge-small)

        Using the document's ingestion model is critical — querying a
        768-dim collection with a 384-dim vector raises an error.
        """
        if override and override not in (None, "auto", ""):
            return override

        if document_id:
            from sqlalchemy import select
            from app.models.document import Document
            result = await self.db.execute(
                select(Document.embedding_model).where(
                    Document.id == document_id,
                    Document.user_id == user_id,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                return row

        # Fallback: query the collection to discover its dimension
        try:
            from app.engines.registry import get_registry
            store = get_registry().get_vector_store("chroma")
            # Peek at first stored vector to infer dimension
            peek = store.get()
            if peek and peek.get("embeddings") and peek["embeddings"]:
                emb = peek["embeddings"][0]
                if isinstance(emb, list) and len(emb) == 768:
                    return "BAAI/bge-base-en-v1.5"
                if isinstance(emb, list) and len(emb) == 1024:
                    return "BAAI/bge-large-en-v1.5"
        except Exception:
            pass

        return "BAAI/bge-small-en-v1.5"

    # ------------------------------------------------------------------
    # Primary entry-point
    # ------------------------------------------------------------------

    async def process_query(
        self,
        query_data: QueryCreate,
        user_id: str,
    ) -> QueryResponse:
        """Process a query end-to-end with policy routing + adaptive escalation."""
        start_time = time.time()

        # ── 1. Persist query record ────────────────────────────────────
        db_query = Query(
            user_id=user_id,
            question=query_data.question,
            document_id=query_data.document_id,
            status=QueryStatus.PROCESSING,
        )
        self.db.add(db_query)
        await self.db.commit()
        await self.db.refresh(db_query)

        try:
            # ── 2. Resolve workflow ────────────────────────────────────
            # Resolve embedding model first — must match ingestion model
            resolved_embedding = await self._resolve_embedding_model(
                document_id=query_data.document_id,
                user_id=user_id,
                override=getattr(query_data, "embedding_model", None),
            )
            workflow = self._policy.resolve_workflow(
                query=query_data.question,
                retrieval_strategy=query_data.retrieval_strategy,
                reranking_strategy=query_data.reranking_strategy,
                prompt_template=query_data.prompt_template,
                embedding_model=resolved_embedding,
            )

            print(
                f"DEBUG: Resolved workflow — "
                f"retrieval={workflow.retrieval_strategy}({workflow.retrieval_mode.value}) "
                f"reranking={workflow.reranking_strategy}({workflow.reranking_mode.value}) "
                f"embedding={workflow.embedding_model}({workflow.embedding_mode.value})",
                flush=True,
            )

            # ── 3. Build engines ───────────────────────────────────────
            embedder = self._registry.get_embedding(workflow.embedding_model)
            vector_store = self._registry.get_vector_store("chroma")
            retriever = self._registry.get_retrieval(workflow.retrieval_strategy, vector_store)
            reranker = self._registry.get_reranking(workflow.reranking_strategy)

            # ── 4. Embed query ─────────────────────────────────────────
            query_embedding = embedder.embed_text(query_data.question)

            # ── 5. Filters ─────────────────────────────────────────────
            filters: Dict[str, Any] = {"user_id": user_id}
            if query_data.document_id:
                filters["document_id"] = query_data.document_id
            if getattr(query_data, "folder_id", None):
                filters["folder_id"] = query_data.folder_id

            n_results = getattr(query_data, "n_results", None) or 5

            # ── 6. Retrieve ────────────────────────────────────────────
            retrieval_start = time.time()
            results = self._do_retrieve(
                retriever=retriever,
                strategy=workflow.retrieval_strategy,
                query_embedding=query_embedding,
                query_text=query_data.question,
                n_results=n_results,
                filters=filters,
            )
            retrieval_time = int((time.time() - retrieval_start) * 1000)
            print(f"DEBUG: Retrieved {len(results)} chunks in {retrieval_time}ms", flush=True)

            # ── 7. Adaptive confidence escalation ─────────────────────
            # Only escalate when the policy chose the strategy (auto mode)
            # so we never override a deliberate manual choice.
            escalated_to: Optional[str] = None
            if (
                results
                and workflow.retrieval_mode.value == "auto"
                and _avg_distance(results) > _LOW_CONFIDENCE_DISTANCE_THRESHOLD
            ):
                next_strategy = _ESCALATION_MAP.get(workflow.retrieval_strategy)
                if next_strategy and next_strategy != workflow.retrieval_strategy:
                    print(
                        f"DEBUG: Low confidence (avg_dist={_avg_distance(results):.3f}) "
                        f"— escalating retrieval {workflow.retrieval_strategy} → {next_strategy}",
                        flush=True,
                    )
                    escalated_retriever = self._registry.get_retrieval(next_strategy, vector_store)
                    escalation_start = time.time()
                    escalated_results = self._do_retrieve(
                        retriever=escalated_retriever,
                        strategy=next_strategy,
                        query_embedding=query_embedding,
                        query_text=query_data.question,
                        n_results=n_results,
                        filters=filters,
                    )
                    # Use escalated results only if they're actually better
                    if (
                        escalated_results
                        and _avg_distance(escalated_results) < _avg_distance(results)
                    ):
                        results = escalated_results
                        escalated_to = next_strategy
                        retrieval_time += int((time.time() - escalation_start) * 1000)
                        print(f"DEBUG: Escalation improved results — using {next_strategy}", flush=True)
                    else:
                        print("DEBUG: Escalation did not improve — keeping original results", flush=True)

            # ── 8. Optional reranking ──────────────────────────────────
            effective_retrieval = escalated_to or workflow.retrieval_strategy
            if reranker and results:
                results = reranker.rerank(results=results, query=query_data.question, top_k=n_results)

            # ── 9. Build context ───────────────────────────────────────
            context = "\n\n".join(r["text"] for r in results)

            # ── 10. Generation params ──────────────────────────────────
            generation_start = time.time()
            reasoning_level_str = getattr(query_data, "reasoning_level", None) or "intermediate"
            try:
                reasoning_level = ReasoningLevel(reasoning_level_str)
            except ValueError:
                reasoning_level = ReasoningLevel.INTERMEDIATE

            reasoning_config = self._template_manager.get_reasoning_config(reasoning_level)
            is_cloud = (
                isinstance(self._generator, (OpenAIInference, OpenRouterInference))
                and not self._generator.offline_mode
            )
            if is_cloud:
                max_tokens = workflow.generation_params.get("max_tokens", reasoning_config["max_tokens"])
                temperature = workflow.generation_params.get("temperature", reasoning_config["temperature"])
                timeout = 60
            else:
                model_config = MODEL_CONFIGS.get(settings.hf_model, MODEL_CONFIGS["Qwen/Qwen2.5-0.5B-Instruct"])
                max_tokens = min(workflow.generation_params.get("max_tokens", reasoning_config["max_tokens"]), model_config["max_tokens"])
                temperature = workflow.generation_params.get("temperature", reasoning_config["temperature"])
                timeout = model_config["timeout"]

            # ── 11. Prompt ─────────────────────────────────────────────
            try:
                prompt_type = PromptType(workflow.prompt_template)
            except ValueError:
                prompt_type = PromptType.FACTUAL_QA

            prompt = self._template_manager.get_template(
                prompt_type=prompt_type,
                query=query_data.question,
                context=context,
            )

            # ── 12. Generate ───────────────────────────────────────────
            generation_result = self._generator.generate_with_context(
                query=query_data.question,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
                template=prompt,
                timeout=timeout,
            )
            generation_time = int((time.time() - generation_start) * 1000)

            # ── 13. Build workflow trace (novel: full audit trail) ─────
            workflow_trace: Dict[str, Any] = {
                # Resolved strategies
                "retrieval_strategy": effective_retrieval,
                "retrieval_mode": workflow.retrieval_mode.value,
                "reranking_strategy": workflow.reranking_strategy,
                "reranking_mode": workflow.reranking_mode.value,
                "embedding_model": workflow.embedding_model,
                "embedding_mode": workflow.embedding_mode.value,
                "prompt_template": workflow.prompt_template,
                "prompt_mode": workflow.prompt_mode.value,
                "chunking_mode": workflow.chunking_mode.value,
                # Intent/complexity signals
                "query_intent": workflow.query_intent,
                "query_complexity": workflow.query_complexity,
                # Auto-selection rationale
                "auto_rationale": workflow.auto_rationale,
                # Adaptive escalation
                "escalated": escalated_to is not None,
                "escalated_from": workflow.retrieval_strategy if escalated_to else None,
                "escalated_to": escalated_to,
                # Confidence signal
                "avg_retrieval_distance": round(_avg_distance(results), 4),
                # Generation params actually used
                "generation_params_used": {
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "timeout": timeout,
                },
            }

            # ── 14. Persist ────────────────────────────────────────────
            provider = (settings.generation_provider or "").lower()
            if provider == "openrouter" and settings.openrouter_api_key:
                gen_model_name = settings.openrouter_model
            elif provider == "openai" and settings.openai_api_key:
                gen_model_name = settings.openai_model
            else:
                gen_model_name = settings.hf_model

            db_query.answer = generation_result["generated_text"]
            db_query.sources = [{"id": r["id"], "text": r["text"][:200]} for r in results]
            db_query.intent = workflow.query_intent
            db_query.complexity_score = workflow.query_complexity
            db_query.retrieval_strategy = effective_retrieval
            db_query.reranking_strategy = workflow.reranking_strategy
            db_query.embedding_model = workflow.embedding_model
            db_query.generation_model = gen_model_name
            db_query.prompt_template = workflow.prompt_template
            db_query.workflow_trace = workflow_trace
            db_query.retrieval_time = retrieval_time
            db_query.generation_time = generation_time
            db_query.total_time = int((time.time() - start_time) * 1000)
            db_query.token_usage = generation_result.get("tokens_used", 0)
            db_query.status = QueryStatus.COMPLETED
            db_query.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(db_query)
            return QueryResponse.model_validate(db_query)

        except Exception as exc:
            db_query.status = QueryStatus.FAILED
            db_query.error_message = str(exc)
            db_query.updated_at = datetime.utcnow()
            await self.db.commit()
            raise

    # ------------------------------------------------------------------
    # Retrieval dispatch
    # ------------------------------------------------------------------

    def _do_retrieve(
        self,
        retriever,
        strategy: str,
        query_embedding: list,
        query_text: str,
        n_results: int,
        filters: dict,
    ) -> list:
        if strategy == "hybrid":
            return retriever.retrieve(
                query_embedding=query_embedding,
                query_text=query_text,
                n_results=n_results,
                filters=filters,
            )
        return retriever.retrieve(
            query_embedding=query_embedding,
            n_results=n_results,
            filters=filters,
        )

    # ------------------------------------------------------------------
    # Public helper used by the evaluation service
    # ------------------------------------------------------------------

    async def process_query_for_eval(
        self,
        question: str,
        user_id: str,
        document_id: Optional[str],
        retrieval_strategy: Optional[str],
        reranking_strategy: Optional[str],
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Lightweight query path for RAGAS evaluation.
        Returns answer + raw context chunks + token/latency metrics.
        Does NOT persist to DB.
        """
        from app.models.query import QueryCreate
        qc = QueryCreate(
            question=question,
            document_id=document_id,
            retrieval_strategy=retrieval_strategy,
            reranking_strategy=reranking_strategy,
            n_results=n_results,
        )

        start = time.time()
        resolved_embedding = await self._resolve_embedding_model(
            document_id=document_id,
            user_id=user_id,
            override=None,
        )
        workflow = self._policy.resolve_workflow(
            query=question,
            retrieval_strategy=retrieval_strategy,
            reranking_strategy=reranking_strategy,
            embedding_model=resolved_embedding,
        )

        embedder = self._registry.get_embedding(workflow.embedding_model)
        vector_store = self._registry.get_vector_store("chroma")
        retriever = self._registry.get_retrieval(workflow.retrieval_strategy, vector_store)
        reranker = self._registry.get_reranking(workflow.reranking_strategy)

        query_embedding = embedder.embed_text(question)
        filters: Dict[str, Any] = {"user_id": user_id}
        if document_id:
            filters["document_id"] = document_id

        results = self._do_retrieve(
            retriever=retriever,
            strategy=workflow.retrieval_strategy,
            query_embedding=query_embedding,
            query_text=question,
            n_results=n_results,
            filters=filters,
        )
        if reranker and results:
            results = reranker.rerank(results=results, query=question, top_k=n_results)

        context_chunks = [r["text"] for r in results]
        context = "\n\n".join(context_chunks)

        is_cloud = (
            isinstance(self._generator, (OpenAIInference, OpenRouterInference))
            and not self._generator.offline_mode
        )
        max_tokens = 512 if is_cloud else 256
        generation_result = self._generator.generate_with_context(
            query=question,
            context=context,
            max_tokens=max_tokens,
            temperature=0.3,
            timeout=60,
        )
        total_ms = int((time.time() - start) * 1000)

        return {
            "answer": generation_result["generated_text"],
            "contexts": context_chunks,
            "tokens_used": generation_result.get("tokens_used", 0),
            "latency_ms": total_ms,
            "retrieval_strategy": workflow.retrieval_strategy,
            "reranking_strategy": workflow.reranking_strategy,
        }

    # ------------------------------------------------------------------
    # History / get
    # ------------------------------------------------------------------

    async def get_query_history(self, user_id: str, skip: int = 0, limit: int = 100) -> List[QueryResponse]:
        result = await self.db.execute(
            select(Query).where(Query.user_id == user_id).offset(skip).limit(limit).order_by(Query.created_at.desc())
        )
        return [QueryResponse.model_validate(q) for q in result.scalars().all()]

    async def get_query(self, query_id: str, user_id: str) -> Optional[QueryResponse]:
        result = await self.db.execute(
            select(Query).where(Query.id == query_id, Query.user_id == user_id)
        )
        q = result.scalar_one_or_none()
        return QueryResponse.model_validate(q) if q else None

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------

    async def process_batch_query(self, batch_data: BatchQueryCreate, user_id: str) -> BatchQueryResponse:
        task_id = str(int(time.time()))
        results, completed, failed = [], 0, 0
        for qd in batch_data.queries:
            try:
                results.append(await self.process_query(qd, user_id))
                completed += 1
            except Exception:
                failed += 1
        return BatchQueryResponse(
            task_id=task_id,
            status="completed",
            total_queries=len(batch_data.queries),
            completed_queries=completed,
            failed_queries=failed,
            results=results,
        )
