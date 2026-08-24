"""
RAGAS Evaluation Engine
-----------------------
Wraps the ragas library with a graceful fallback so the application starts
even when ragas / datasets are not installed.  Install both to enable real
scoring:

    pip install ragas datasets

Without them the evaluator returns placeholder scores of 0.0 and logs a
warning — useful for development without the full ML dependency stack.
"""
from __future__ import annotations

import importlib
import warnings
from typing import Any, Dict, List, Optional


def _ragas_available() -> bool:
    try:
        importlib.import_module("ragas")
        importlib.import_module("datasets")
        return True
    except ImportError:
        return False


class RAGASEvaluation:
    """RAGAS-based evaluation for RAG systems."""

    def __init__(self) -> None:
        self.available = _ragas_available()
        if not self.available:
            warnings.warn(
                "ragas/datasets not installed — evaluation will return placeholder scores. "
                "Run: pip install ragas datasets",
                stacklevel=2,
            )

    # ------------------------------------------------------------------
    # Primary entry-point
    # ------------------------------------------------------------------

    def evaluate(
        self,
        queries: List[str],
        answers: List[str],
        contexts: List[List[str]],
        ground_truths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Score a batch of query-answer-context triples.

        Parameters
        ----------
        queries:       List of question strings.
        answers:       List of generated answer strings.
        contexts:      List of retrieved context lists (one list per query).
        ground_truths: Optional list of reference answers (enables context_recall).

        Returns
        -------
        Dict with faithfulness, answer_relevancy, context_precision,
        context_recall (or None), overall_score.
        """
        if not self.available:
            return self._placeholder(len(queries), has_gt=bool(ground_truths))

        try:
            from ragas import evaluate as ragas_evaluate
            from ragas.metrics import (
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            )
            from datasets import Dataset

            data: Dict[str, Any] = {
                "question": queries,
                "answer": answers,
                "contexts": contexts,
            }
            metrics = [faithfulness, answer_relevancy, context_precision]

            if ground_truths:
                data["ground_truth"] = ground_truths
                metrics.append(context_recall)

            dataset = Dataset.from_dict(data)
            result = ragas_evaluate(dataset=dataset, metrics=metrics)

            scores = {
                "faithfulness": float(result["faithfulness"]),
                "answer_relevancy": float(result["answer_relevancy"]),
                "context_precision": float(result["context_precision"]),
                "context_recall": float(result["context_recall"]) if ground_truths else None,
            }
            scores["overall_score"] = self._overall(scores)
            return scores

        except Exception as exc:
            warnings.warn(f"RAGAS evaluation failed: {exc}. Returning placeholders.", stacklevel=2)
            return self._placeholder(len(queries), has_gt=bool(ground_truths))

    def evaluate_single(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.evaluate(
            queries=[query],
            answers=[answer],
            contexts=[contexts],
            ground_truths=[ground_truth] if ground_truth else None,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _overall(scores: Dict[str, Any]) -> float:
        vals = [v for v in scores.values() if v is not None and isinstance(v, float)]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    @staticmethod
    def _placeholder(n: int, has_gt: bool) -> Dict[str, Any]:
        """Return zero scores when ragas is unavailable."""
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0 if has_gt else None,
            "overall_score": 0.0,
            "_placeholder": True,
        }

    def get_evaluation_info(self) -> Dict[str, Any]:
        return {
            "framework": "ragas",
            "available": self.available,
            "metrics": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
        }
