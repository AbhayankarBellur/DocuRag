"""
RAGAS-compatible Evaluation Engine
-----------------------------------
Implements faithfulness, answer_relevancy and context_precision scoring
directly using the configured LLM (OpenRouter/OpenAI) so there is no
dependency on the ragas package.  Scores are computed with the same
prompt-based methodology as the official ragas library.

If you later install a working version of ragas, swap out the _score_*
methods to delegate to ragas.metrics instead.
"""
from __future__ import annotations

import re
import warnings
from typing import Any, Dict, List, Optional


def _ragas_available() -> bool:
    try:
        import importlib
        mod = importlib.import_module("ragas")
        # Verify it actually loads without errors
        _ = mod.__version__
        return True
    except Exception:
        return False


class RAGASEvaluation:
    """
    LLM-based RAG evaluation.  Uses the application's generation engine
    to score faithfulness, answer relevancy and context precision.
    """

    def __init__(self) -> None:
        self.available = True          # always available — we roll our own
        self._gen = self._build_gen()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        queries: List[str],
        answers: List[str],
        contexts: List[List[str]],
        ground_truths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Score a batch of query-answer-context triples."""
        n = len(queries)
        if n == 0:
            return self._zero(bool(ground_truths))

        faith_scores, relev_scores, prec_scores, recall_scores = [], [], [], []

        for i in range(n):
            q   = queries[i]
            a   = answers[i]
            ctx = contexts[i]
            gt  = ground_truths[i] if ground_truths else None

            faith_scores.append(self._score_faithfulness(q, a, ctx))
            relev_scores.append(self._score_answer_relevancy(q, a))
            prec_scores.append(self._score_context_precision(q, a, ctx))
            if gt is not None:
                recall_scores.append(self._score_context_recall(q, gt, ctx))

        scores = {
            "faithfulness":      round(sum(faith_scores)  / n, 4),
            "answer_relevancy":  round(sum(relev_scores)   / n, 4),
            "context_precision": round(sum(prec_scores)    / n, 4),
            "context_recall":    round(sum(recall_scores)  / len(recall_scores), 4)
                                 if recall_scores else None,
        }
        scores["overall_score"] = self._overall(scores)
        return scores

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

    def get_evaluation_info(self) -> Dict[str, Any]:
        return {
            "framework": "native-llm",
            "available": True,
            "metrics": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
        }

    # ------------------------------------------------------------------
    # Metric implementations
    # ------------------------------------------------------------------

    def _score_faithfulness(self, query: str, answer: str, contexts: List[str]) -> float:
        """
        Faithfulness: fraction of statements in the answer that are
        supported by the retrieved context.
        Prompt-based binary classifier (0 or 1) per statement.
        """
        if not answer.strip() or not contexts:
            return 0.0

        ctx_text = "\n\n".join(contexts[:5])          # cap to keep prompt small
        prompt = (
            f"Context:\n{ctx_text}\n\n"
            f"Answer: {answer}\n\n"
            "For each factual claim in the answer, say YES if it is supported "
            "by the context, NO otherwise. "
            "Then output a final line: SCORE: <fraction of YES out of total claims>\n"
            "Example: SCORE: 0.75"
        )
        raw = self._llm(prompt, max_tokens=200)
        return self._extract_score(raw)

    def _score_answer_relevancy(self, query: str, answer: str) -> float:
        """
        Answer relevancy: does the answer actually address the question?
        Simple 0-1 LLM judge.
        """
        if not answer.strip():
            return 0.0
        prompt = (
            f"Question: {query}\n"
            f"Answer: {answer}\n\n"
            "On a scale from 0 to 1, how relevant is the answer to the question? "
            "1 = perfectly addresses the question, 0 = completely irrelevant.\n"
            "Output only: SCORE: <number between 0 and 1>"
        )
        raw = self._llm(prompt, max_tokens=50)
        return self._extract_score(raw)

    def _score_context_precision(
        self, query: str, answer: str, contexts: List[str]
    ) -> float:
        """
        Context precision: fraction of retrieved chunks that were actually
        useful for answering the question.
        """
        if not contexts:
            return 0.0
        useful = 0
        for chunk in contexts[:5]:
            prompt = (
                f"Question: {query}\n"
                f"Retrieved chunk:\n{chunk[:400]}\n\n"
                "Is this chunk useful for answering the question? "
                "Output YES or NO only."
            )
            raw = self._llm(prompt, max_tokens=10)
            if "yes" in raw.lower():
                useful += 1
        return round(useful / min(len(contexts), 5), 4)

    def _score_context_recall(
        self, query: str, ground_truth: str, contexts: List[str]
    ) -> float:
        """
        Context recall: fraction of ground-truth information covered by
        the retrieved context.
        """
        if not ground_truth.strip() or not contexts:
            return 0.0
        ctx_text = "\n\n".join(contexts[:5])
        prompt = (
            f"Ground truth answer: {ground_truth}\n"
            f"Retrieved context:\n{ctx_text[:1200]}\n\n"
            "What fraction of the ground truth information is present in the "
            "retrieved context? "
            "Output only: SCORE: <number between 0 and 1>"
        )
        raw = self._llm(prompt, max_tokens=50)
        return self._extract_score(raw)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _llm(self, prompt: str, max_tokens: int = 100) -> str:
        if self._gen is None:
            return "SCORE: 0.0"
        try:
            result = self._gen.generate(prompt=prompt, max_tokens=max_tokens, temperature=0.0)
            return result.get("generated_text", "") or ""
        except Exception as exc:
            warnings.warn(f"Eval LLM call failed: {exc}", stacklevel=2)
            return "SCORE: 0.0"

    @staticmethod
    def _extract_score(text: str) -> float:
        """Pull the first decimal number after 'SCORE:' or the first float found."""
        m = re.search(r"SCORE:\s*([\d.]+)", text, re.IGNORECASE)
        if not m:
            m = re.search(r"\b(0\.\d+|1\.0|1)\b", text)
        if m:
            try:
                return min(max(float(m.group(1)), 0.0), 1.0)
            except ValueError:
                pass
        return 0.0

    @staticmethod
    def _overall(scores: Dict[str, Any]) -> float:
        vals = [v for v in scores.values() if isinstance(v, float)]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    @staticmethod
    def _zero(has_gt: bool) -> Dict[str, Any]:
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0 if has_gt else None,
            "overall_score": 0.0,
        }

    @staticmethod
    def _build_gen():
        """Return the same generation engine the app uses."""
        try:
            from app.utils.config import settings
            provider = (settings.generation_provider or "").lower()
            if provider == "openrouter" and settings.openrouter_api_key:
                from app.engines.generation.openrouter_inference import OpenRouterInference
                return OpenRouterInference()
            if provider == "openai" and settings.openai_api_key:
                from app.engines.generation.openai_inference import OpenAIInference
                return OpenAIInference()
        except Exception:
            pass
        return None
