"""Query Service"""
from __future__ import annotations

import time
from datetime import datetime
from typing import List, Optional

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
from app.utils.config import settings

# Generation / prompt imports (unchanged)
from app.engines.generation.hf_inference import HFInference
from app.engines.generation.openai_inference import OpenAIInference
from app.engines.generation.openrouter_inference import OpenRouterInference
from app.engines.prompting.template_manager import (
    MODEL_CONFIGS,
    PromptType,
    ReasoningLevel,
    TemplateManager,
)


def _build_generator():
    """Return the configured generation engine based on GENERATION_PROVIDER."""
    provider = (settings.generation_provider or "huggingface").lower()

    if provider == "openrouter" and settings.openrouter_api_key:
        print(
            f"INFO: Using OpenRouter generator — model={settings.openrouter_model}",
            flush=True,
        )
        return OpenRouterInference(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
        )

    if provider == "openai" and settings.openai_api_key:
        print(
            f"INFO: Using OpenAI generator — model={settings.openai_model}",
            flush=True,
        )
        return OpenAIInference(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    print("INFO: Using HuggingFace generator", flush=True)
    return HFInference()


class QueryService:
    """Query processing service with policy-driven strategy selection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._policy = PolicyEngine()
        self._registry = get_registry()
        self._generator = _build_generator()
        self._template_manager = TemplateManager()

    # ------------------------------------------------------------------
    # Primary entry-point
    # ------------------------------------------------------------------

    async def process_query(
        self,
        query_data: QueryCreate,
        user_id: str,
    ) -> QueryResponse:
        """Process a query end-to-end with auto or manual strategy selection."""
        start_time = time.time()

        # ── 1. Persist query record (status = PROCESSING) ─────────────
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
            # ── 2. Resolve workflow via PolicyEngine ───────────────────
            workflow = self._policy.resolve_workflow(
                query=query_data.question,
                retrieval_strategy=query_data.retrieval_strategy,
                reranking_strategy=query_data.reranking_strategy,
                prompt_template=query_data.prompt_template,
                # embedding_model and chunking_strategy are doc-time concerns;
                # at query time they come from QueryCreate's optional fields
                embedding_model=getattr(query_data, "embedding_model", None),
            )

            print(
                f"DEBUG: Resolved workflow — retrieval={workflow.retrieval_strategy} "
                f"({workflow.retrieval_mode.value}), "
                f"reranking={workflow.reranking_strategy} "
                f"({workflow.reranking_mode.value}), "
                f"embedding={workflow.embedding_model} "
                f"({workflow.embedding_mode.value})",
                flush=True,
            )

            # ── 3. Build engines from registry ────────────────────────
            embedder = self._registry.get_embedding(workflow.embedding_model)
            vector_store = self._registry.get_vector_store("chroma")
            retriever = self._registry.get_retrieval(
                workflow.retrieval_strategy, vector_store
            )
            reranker = self._registry.get_reranking(workflow.reranking_strategy)

            # ── 4. Embed query ─────────────────────────────────────────
            query_embedding = embedder.embed_text(query_data.question)

            # ── 5. Build metadata filters ──────────────────────────────
            filters: dict = {"user_id": user_id}
            if query_data.document_id:
                filters["document_id"] = query_data.document_id
            if getattr(query_data, "folder_id", None):
                filters["folder_id"] = query_data.folder_id

            n_results = getattr(query_data, "n_results", None) or 5
            print(
                f"DEBUG: Retrieving {n_results} results via "
                f"'{workflow.retrieval_strategy}' with filters: {filters}",
                flush=True,
            )

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
            print(f"DEBUG: Retrieved {len(results)} chunks", flush=True)
            retrieval_time = int((time.time() - retrieval_start) * 1000)

            # ── 7. Optional reranking ──────────────────────────────────
            if reranker and results:
                print(
                    f"DEBUG: Reranking with '{workflow.reranking_strategy}'",
                    flush=True,
                )
                results = reranker.rerank(
                    results=results,
                    query=query_data.question,
                    top_k=n_results,
                )

            # ── 8. Build context ───────────────────────────────────────
            context = "\n\n".join(r["text"] for r in results)

            # ── 9. Resolve generation parameters ──────────────────────
            generation_start = time.time()

            reasoning_level_str = (
                getattr(query_data, "reasoning_level", None) or "intermediate"
            )
            try:
                reasoning_level = ReasoningLevel(reasoning_level_str)
            except ValueError:
                reasoning_level = ReasoningLevel.INTERMEDIATE

            reasoning_config = self._template_manager.get_reasoning_config(
                reasoning_level
            )

            # OpenAI / OpenRouter have generous token limits; HF needs the MODEL_CONFIGS cap
            is_openai = (
                isinstance(self._generator, (OpenAIInference, OpenRouterInference))
                and not self._generator.offline_mode
            )
            if is_openai:
                max_tokens = workflow.generation_params.get(
                    "max_tokens", reasoning_config["max_tokens"]
                )
                temperature = workflow.generation_params.get(
                    "temperature", reasoning_config["temperature"]
                )
                timeout = 60
            else:
                model_config = MODEL_CONFIGS.get(
                    settings.hf_model,
                    MODEL_CONFIGS["Qwen/Qwen2.5-0.5B-Instruct"],
                )
                policy_max_tokens = workflow.generation_params.get(
                    "max_tokens", reasoning_config["max_tokens"]
                )
                max_tokens = min(policy_max_tokens, model_config["max_tokens"])
                temperature = workflow.generation_params.get(
                    "temperature", reasoning_config["temperature"]
                )
                timeout = model_config["timeout"]

            # ── 10. Build prompt ───────────────────────────────────────
            prompt_type_str = workflow.prompt_template
            try:
                prompt_type = PromptType(prompt_type_str)
            except ValueError:
                prompt_type = PromptType.FACTUAL_QA

            prompt = self._template_manager.get_template(
                prompt_type=prompt_type,
                query=query_data.question,
                context=context,
            )
            print(
                f"DEBUG: prompt_template='{workflow.prompt_template}' "
                f"max_tokens={max_tokens} temperature={temperature}",
                flush=True,
            )

            # ── 11. Generate ───────────────────────────────────────────
            generation_result = self._generator.generate_with_context(
                query=query_data.question,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
                template=prompt,
                timeout=timeout,
            )
            generation_time = int((time.time() - generation_start) * 1000)
            print(
                f"DEBUG: Generation done — "
                f"{len(generation_result.get('generated_text', ''))} chars",
                flush=True,
            )

            # ── 12. Persist completed query ───────────────────────────
            db_query.answer = generation_result["generated_text"]
            db_query.sources = [
                {"id": r["id"], "text": r["text"][:200]} for r in results
            ]
            db_query.intent = workflow.query_intent
            db_query.complexity_score = workflow.query_complexity
            db_query.retrieval_strategy = workflow.retrieval_strategy
            db_query.reranking_strategy = workflow.reranking_strategy
            db_query.embedding_model = workflow.embedding_model
            provider = (settings.generation_provider or "").lower()
            if provider == "openrouter" and settings.openrouter_api_key:
                gen_model_name = settings.openrouter_model
            elif provider == "openai" and settings.openai_api_key:
                gen_model_name = settings.openai_model
            else:
                gen_model_name = settings.hf_model
            db_query.generation_model = gen_model_name
            db_query.prompt_template = workflow.prompt_template
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
    # Retrieval dispatch helper
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
        """Dispatch to the right retriever signature based on strategy."""
        if strategy == "hybrid":
            return retriever.retrieve(
                query_embedding=query_embedding,
                query_text=query_text,
                n_results=n_results,
                filters=filters,
            )
        if strategy == "mmr":
            return retriever.retrieve(
                query_embedding=query_embedding,
                n_results=n_results,
                filters=filters,
            )
        # similarity (default)
        return retriever.retrieve(
            query_embedding=query_embedding,
            n_results=n_results,
            filters=filters,
        )

    # ------------------------------------------------------------------
    # History / read helpers (unchanged)
    # ------------------------------------------------------------------

    async def get_query_history(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[QueryResponse]:
        result = await self.db.execute(
            select(Query)
            .where(Query.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Query.created_at.desc())
        )
        return [QueryResponse.model_validate(q) for q in result.scalars().all()]

    async def get_query(
        self,
        query_id: str,
        user_id: str,
    ) -> Optional[QueryResponse]:
        result = await self.db.execute(
            select(Query).where(
                Query.id == query_id, Query.user_id == user_id
            )
        )
        query = result.scalar_one_or_none()
        return QueryResponse.model_validate(query) if query else None

    # ------------------------------------------------------------------
    # Batch (delegates to process_query)
    # ------------------------------------------------------------------

    async def process_batch_query(
        self,
        batch_data: BatchQueryCreate,
        user_id: str,
    ) -> BatchQueryResponse:
        task_id = str(int(time.time()))
        results = []
        completed = failed = 0

        for query_data in batch_data.queries:
            try:
                result = await self.process_query(query_data, user_id)
                results.append(result)
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
