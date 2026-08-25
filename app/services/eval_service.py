"""
Evaluation Service
------------------
Orchestrates multi-condition RAGAS evaluation runs.

Each run executes every golden QA item under every requested condition,
collects RAGAS metrics + token/latency measurements, and returns a
structured comparison result.

Condition definitions
~~~~~~~~~~~~~~~~~~~~~
auto               – all strategies resolved by the policy engine
similarity         – similarity retrieval, no reranking
hybrid_bm25        – hybrid retrieval + BM25 reranking
mmr_cross_encoder  – MMR retrieval + cross-encoder reranking
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.evaluation.ragas_eval import RAGASEvaluation


# ── Condition → (retrieval, reranking) mapping ───────────────────────────────
CONDITION_CONFIGS: Dict[str, Dict[str, Optional[str]]] = {
    "auto":               {"retrieval_strategy": None,          "reranking_strategy": None},
    "similarity":         {"retrieval_strategy": "similarity",  "reranking_strategy": "none"},
    "hybrid_bm25":        {"retrieval_strategy": "hybrid",      "reranking_strategy": "bm25"},
    "mmr_cross_encoder":  {"retrieval_strategy": "mmr",         "reranking_strategy": "cross_encoder"},
}


class EvalService:
    """Runs structured RAGAS evaluation comparisons."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._ragas = RAGASEvaluation()

    async def run_comparison(
        self,
        golden_items: List[Dict[str, Any]],
        user_id: str,
        conditions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run a full evaluation comparison.

        Parameters
        ----------
        golden_items : list of dicts with keys: question, ground_truth, document_id (optional)
        user_id      : owner user ID (used for retrieval filters)
        conditions   : subset of CONDITION_CONFIGS keys; defaults to all four

        Returns
        -------
        Dict with run_id and per-condition EvalRunResult dicts.
        """
        from app.services.query_service import QueryService

        run_id = str(uuid.uuid4())[:8]
        conditions = [c for c in (conditions or list(CONDITION_CONFIGS.keys()))
                      if c in CONDITION_CONFIGS]

        query_service = QueryService(self.db)
        results: List[Dict[str, Any]] = []

        for condition in conditions:
            cfg = CONDITION_CONFIGS[condition]
            queries, answers, contexts, ground_truths = [], [], [], []
            total_tokens, total_latency = 0, 0

            for item in golden_items:
                question = item.get("question", "").strip()
                gt = item.get("ground_truth", "").strip()
                doc_id = item.get("document_id") or None
                if not question:
                    continue

                try:
                    outcome = await query_service.process_query_for_eval(
                        question=question,
                        user_id=user_id,
                        document_id=doc_id,
                        retrieval_strategy=cfg["retrieval_strategy"],
                        reranking_strategy=cfg["reranking_strategy"],
                        n_results=10,
                    )
                    queries.append(question)
                    answers.append(outcome["answer"])
                    contexts.append(outcome["contexts"])
                    ground_truths.append(gt)
                    total_tokens += outcome.get("tokens_used", 0)
                    total_latency += outcome.get("latency_ms", 0)
                except Exception as exc:
                    print(f"WARNING: eval item failed for condition={condition}: {exc}", flush=True)

            n = max(len(queries), 1)
            scores = self._ragas.evaluate(
                queries=queries,
                answers=answers,
                contexts=contexts,
                ground_truths=ground_truths if any(ground_truths) else None,
            )

            results.append({
                "condition": condition,
                "config": {
                    "retrieval": cfg["retrieval_strategy"] or "auto",
                    "reranking": cfg["reranking_strategy"] or "auto",
                },
                "faithfulness": scores["faithfulness"],
                "answer_relevancy": scores["answer_relevancy"],
                "context_precision": scores["context_precision"],
                "context_recall": scores["context_recall"],
                "overall_score": scores["overall_score"],
                "avg_tokens": round(total_tokens / n, 1),
                "avg_latency_ms": round(total_latency / n, 1),
                "n_items": len(queries),
                "ragas_placeholder": scores.get("_placeholder", False),
            })

        return {"run_id": run_id, "results": results}
