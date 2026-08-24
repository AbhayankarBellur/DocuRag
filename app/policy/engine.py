"""
Policy Engine Orchestrator
--------------------------
Central decision point that converts raw signals (document content, query text,
explicit user overrides) into a fully-resolved :class:`WorkflowConfig`.

Design rules
~~~~~~~~~~~~
* Any strategy value of ``None`` or ``"auto"`` triggers automatic selection.
* Any explicit strategy value is accepted as-is (validated against allowed sets
  by the EngineRegistry when the engine is actually instantiated).
* ``resolve_workflow()`` is the single public entry-point used by both
  ``DocumentService`` and ``QueryService``.
* Legacy helpers (``process_document``, ``process_query``, ``get_full_workflow``)
  are kept for backward compatibility but now delegate to ``resolve_workflow()``.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.policy.document_analyzer import DocumentAnalyzer
from app.policy.query_analyzer import QueryAnalyzer
from app.policy.models import WorkflowConfig, StrategyMode


_AUTO_SENTINELS = frozenset({"auto", "Auto", "AUTO", "", None})


def _is_auto(value: Optional[str]) -> bool:
    return value in _AUTO_SENTINELS


class PolicyEngine:
    """Policy Engine for dynamic workflow selection."""

    def __init__(self) -> None:
        self.document_analyzer = DocumentAnalyzer()
        self.query_analyzer = QueryAnalyzer()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def resolve_workflow(
        self,
        *,
        # Content signals (at least one should be provided)
        document_content: Optional[str] = None,
        document_metadata: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        # Explicit overrides — None / "auto" → auto-select
        chunking_strategy: Optional[str] = None,
        embedding_model: Optional[str] = None,
        retrieval_strategy: Optional[str] = None,
        reranking_strategy: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> WorkflowConfig:
        """
        Resolve a complete :class:`WorkflowConfig`.

        For every strategy field the caller can either:

        * Pass ``None`` or ``"auto"`` → the engine auto-selects based on
          document / query signals.
        * Pass a concrete value (e.g. ``"hybrid"``) → that value is used
          directly and its ``*_mode`` is set to ``MANUAL``.

        Parameters
        ----------
        document_content:
            Raw text of the document being ingested (used for doc-level
            strategy selection).
        document_metadata:
            Additional metadata dict from the ingestion engine.
        query:
            User query string (used for query-level strategy selection).
        chunking_strategy, embedding_model, retrieval_strategy,
        reranking_strategy, prompt_template:
            Optional explicit overrides.  Pass ``"auto"`` or ``None`` to let
            the engine decide.

        Returns
        -------
        WorkflowConfig
            Fully resolved, ready-to-use workflow configuration.
        """
        cfg = WorkflowConfig()

        # ── 1. Run analyzers to collect signals ───────────────────────
        doc_analysis: Dict[str, Any] = {}
        query_analysis: Dict[str, Any] = {}

        if document_content:
            doc_analysis = self.document_analyzer.analyze(
                document_content, document_metadata
            )
            cfg.document_domain = doc_analysis.get("domain")
            cfg.document_complexity = doc_analysis.get("complexity")

        if query:
            query_analysis = self.query_analyzer.analyze(query)
            cfg.query_intent = (
                query_analysis["intent"].value
                if hasattr(query_analysis.get("intent"), "value")
                else str(query_analysis.get("intent", "factual"))
            )
            cfg.query_complexity = query_analysis.get("complexity")

        # ── 2. Resolve each strategy (override → auto-select fallback) ─

        # -- chunking --
        if not _is_auto(chunking_strategy):
            cfg.chunking_strategy = chunking_strategy  # type: ignore[assignment]
            cfg.chunking_mode = StrategyMode.MANUAL
        elif doc_analysis:
            cfg.chunking_strategy = doc_analysis["recommended_chunking"]
            cfg.chunking_mode = StrategyMode.AUTO
            cfg.auto_rationale["chunking"] = doc_analysis.get("rationale", {}).get(
                "chunking", "Auto-selected based on document structure."
            )
        # else: keep dataclass defaults (fixed / AUTO)

        # -- embedding --
        if not _is_auto(embedding_model):
            cfg.embedding_model = embedding_model  # type: ignore[assignment]
            cfg.embedding_mode = StrategyMode.MANUAL
        elif doc_analysis:
            cfg.embedding_model = doc_analysis["recommended_embedding"]
            cfg.embedding_mode = StrategyMode.AUTO
            cfg.auto_rationale["embedding"] = doc_analysis.get("rationale", {}).get(
                "embedding", "Auto-selected based on document complexity."
            )
        # else: keep defaults

        # -- retrieval --
        # Query-level recommendation takes precedence over doc-level when
        # both are available.
        if not _is_auto(retrieval_strategy):
            cfg.retrieval_strategy = retrieval_strategy  # type: ignore[assignment]
            cfg.retrieval_mode = StrategyMode.MANUAL
        elif query_analysis:
            cfg.retrieval_strategy = query_analysis["recommended_retrieval"]
            cfg.retrieval_mode = StrategyMode.AUTO
            cfg.auto_rationale["retrieval"] = query_analysis.get("rationale", {}).get(
                "retrieval", "Auto-selected based on query intent and complexity."
            )
        elif doc_analysis:
            cfg.retrieval_strategy = doc_analysis["recommended_retrieval"]
            cfg.retrieval_mode = StrategyMode.AUTO
            cfg.auto_rationale["retrieval"] = doc_analysis.get("rationale", {}).get(
                "retrieval", "Auto-selected based on document domain."
            )
        # else: keep defaults (similarity)

        # -- reranking --
        if not _is_auto(reranking_strategy):
            # Caller passed an explicit value — could be "none" to disable
            if reranking_strategy and reranking_strategy.lower() not in ("none", "null"):
                cfg.reranking_strategy = reranking_strategy
            else:
                cfg.reranking_strategy = None
            cfg.reranking_mode = StrategyMode.MANUAL
        elif query_analysis:
            cfg.reranking_strategy = query_analysis["recommended_reranking"]
            cfg.reranking_mode = StrategyMode.AUTO
            if cfg.reranking_strategy:
                cfg.auto_rationale["reranking"] = query_analysis.get(
                    "rationale", {}
                ).get("reranking", "Auto-selected based on query complexity.")
            else:
                cfg.auto_rationale["reranking"] = "No reranking needed for this query."
        # else: keep default (None)

        # -- prompt template --
        if not _is_auto(prompt_template):
            cfg.prompt_template = prompt_template  # type: ignore[assignment]
            cfg.prompt_mode = StrategyMode.MANUAL
        elif query_analysis:
            cfg.prompt_template = query_analysis["recommended_template"]
            cfg.prompt_mode = StrategyMode.AUTO
            cfg.auto_rationale["prompt_template"] = (
                f"Template '{cfg.prompt_template}' matched query intent "
                f"'{cfg.query_intent}'."
            )
        # else: keep default (factual_qa)

        # ── 3. Tune generation parameters ────────────────────────────
        self._tune_generation_params(cfg, query_analysis)

        return cfg

    # ------------------------------------------------------------------
    # Generation param tuning (intent-aware)
    # ------------------------------------------------------------------

    def _tune_generation_params(
        self,
        cfg: WorkflowConfig,
        query_analysis: Dict[str, Any],
    ) -> None:
        intent_str = cfg.query_intent or "factual"
        complexity = cfg.query_complexity or 1

        # Start from sensible defaults
        params = {"max_tokens": 512, "temperature": 0.7, "top_p": 0.9}

        if intent_str == "creative":
            params.update(max_tokens=768, temperature=0.9)
        elif intent_str == "factual":
            params.update(max_tokens=256, temperature=0.3)
        elif intent_str in ("analytical", "comparison"):
            params.update(max_tokens=640, temperature=0.5)

        # Longer answers for complex queries
        if complexity >= 4:
            params["max_tokens"] = min(params["max_tokens"] + 256, 1024)

        cfg.generation_params = params

    # ------------------------------------------------------------------
    # Legacy helpers (backward compat — thin wrappers around resolve_workflow)
    # ------------------------------------------------------------------

    def process_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Legacy API — returns dict with 'analysis' and 'workflow' keys."""
        analysis = self.document_analyzer.analyze(content, metadata)
        workflow = self.resolve_workflow(
            document_content=content,
            document_metadata=metadata,
        )
        return {"analysis": analysis, "workflow": workflow.to_dict()}

    def process_query(
        self,
        query: str,
        document_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Legacy API — returns dict with 'analysis' and 'workflow' keys."""
        analysis = self.query_analyzer.analyze(query)
        workflow = self.resolve_workflow(query=query)
        return {"analysis": analysis, "workflow": workflow.to_dict()}

    def get_full_workflow(
        self,
        document_content: Optional[str] = None,
        document_metadata: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Legacy API — returns the workflow dict directly."""
        return self.resolve_workflow(
            document_content=document_content,
            document_metadata=document_metadata,
            query=query,
        ).to_dict()

    def evaluate_workflow_performance(
        self,
        workflow: Dict[str, Any],
        metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """Evaluate workflow performance and suggest improvements."""
        evaluation: Dict[str, Any] = {
            "workflow": workflow,
            "metrics": metrics,
            "score": self._calculate_score(metrics),
            "suggestions": [],
        }

        if metrics.get("relevance", 1.0) < 0.7:
            evaluation["suggestions"].append(
                "Consider switching to semantic chunking for better relevance."
            )
        if metrics.get("latency", 0) > 3000:
            evaluation["suggestions"].append(
                "Consider a smaller embedding model to reduce processing time."
            )
        if metrics.get("diversity", 1.0) < 0.5:
            evaluation["suggestions"].append(
                "Consider MMR retrieval for more diverse results."
            )

        return evaluation

    def _calculate_score(self, metrics: Dict[str, float]) -> float:
        weights = {
            "relevance": 0.4,
            "latency": 0.2,
            "diversity": 0.2,
            "user_satisfaction": 0.2,
        }
        score = 0.0
        total_weight = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                value = metrics[metric]
                if metric == "latency":
                    value = max(0.0, 1.0 - value / 5000.0)
                score += value * weight
                total_weight += weight
        return score / total_weight if total_weight > 0 else 0.0
