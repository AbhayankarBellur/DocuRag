"""Query Analyzer for Policy Engine"""
from typing import Dict, Any, List
import re
from app.models.query import QueryIntent


class QueryAnalyzer:
    """Analyzes queries to determine optimal retrieval and generation strategies."""

    _STOP_WORDS = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "under", "again", "further", "then", "once",
    })

    _INTENT_PATTERNS: Dict[QueryIntent, List[str]] = {
        QueryIntent.FACTUAL: [
            r"\bwhat is\b", r"\bwho is\b", r"\bwhen did\b", r"\bwhere is\b",
            r"\bhow many\b", r"\blist\b", r"\bdefine\b", r"\bexplain\b",
            r"\bname\b", r"\bidentify\b",
        ],
        QueryIntent.ANALYTICAL: [
            r"\bwhy\b", r"\bhow does\b", r"\banalyze\b", r"\banalyse\b",
            r"\bevaluate\b", r"\bassess\b", r"\brelationship\b",
            r"\bimpact of\b", r"\beffect of\b", r"\bimplications\b",
        ],
        QueryIntent.COMPARISON: [
            r"\bdifference between\b", r"\bcompare\b", r"\bversus\b",
            r"\bvs\b", r"\bbetter\b", r"\bpros and cons\b",
            r"\bsimilarities\b", r"\bdistinction\b",
        ],
        QueryIntent.CREATIVE: [
            r"\bwrite\b", r"\bcreate\b", r"\bgenerate\b", r"\bimagine\b",
            r"\bstory\b", r"\bpoem\b", r"\bcreative\b", r"\bdraft\b",
        ],
    }

    # Multi-hop / cross-document indicators
    _MULTI_HOP_PATTERNS = [
        r"\bbecause\b", r"\btherefore\b", r"\bsince\b", r"\bdue to\b",
        r"\bas a result\b", r"\bconsequently\b", r"\bleads to\b",
        r"\brelated to\b", r"\bbased on\b",
    ]

    # Temporal indicators
    _TEMPORAL_PATTERNS = [
        r"\bbefore\b", r"\bafter\b", r"\bduring\b", r"\btimeline\b",
        r"\bhistory\b", r"\bevolution\b", r"\bchanges over\b",
    ]

    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine intent, complexity, and recommended strategies.

        Returns a dict of signals + recommended strategies (with rationale).
        """
        intent = self._classify_intent(query)
        complexity = self._assess_complexity(query)
        keywords = self._extract_keywords(query)
        is_multi_hop = self._is_multi_hop(query)
        is_temporal = self._is_temporal(query)
        word_count = len(query.split())

        analysis: Dict[str, Any] = {
            "intent": intent,
            "complexity": complexity,
            "keywords": keywords,
            "is_multi_hop": is_multi_hop,
            "is_temporal": is_temporal,
            "word_count": word_count,
            "recommended_retrieval": None,
            "recommended_reranking": None,
            "recommended_template": None,
            "rationale": {},
        }

        analysis["recommended_retrieval"] = self._recommend_retrieval(analysis)
        analysis["recommended_reranking"] = self._recommend_reranking(analysis)
        analysis["recommended_template"] = self._recommend_template(analysis)

        return analysis

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def _classify_intent(self, query: str) -> QueryIntent:
        q = query.lower()
        for intent, patterns in self._INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q):
                    return intent
        return QueryIntent.FACTUAL

    def _assess_complexity(self, query: str) -> int:
        q = query.lower()
        complexity = 1

        if self._is_multi_hop(query):
            complexity += 1
        if self._is_temporal(query):
            complexity += 1
        if re.search(r"\bcompare\b|\bdifference\b|\bversus\b|\bvs\b", q):
            complexity += 1
        if len(query.split()) > 15:
            complexity += 1

        return min(complexity, 5)

    def _is_multi_hop(self, query: str) -> bool:
        q = query.lower()
        return any(re.search(p, q) for p in self._MULTI_HOP_PATTERNS)

    def _is_temporal(self, query: str) -> bool:
        q = query.lower()
        return any(re.search(p, q) for p in self._TEMPORAL_PATTERNS)

    def _extract_keywords(self, query: str) -> List[str]:
        words = re.findall(r"\w+", query.lower())
        return [w for w in words if w not in self._STOP_WORDS and len(w) > 2]

    # ------------------------------------------------------------------
    # Recommendation helpers
    # ------------------------------------------------------------------

    def _recommend_retrieval(self, analysis: Dict[str, Any]) -> str:
        rationale = analysis["rationale"]
        intent = analysis["intent"]
        complexity = analysis["complexity"]

        if intent == QueryIntent.ANALYTICAL or analysis["is_multi_hop"]:
            rationale["retrieval"] = (
                "Analytical / multi-hop query — hybrid retrieval combines semantic "
                "vector search with keyword coverage."
            )
            return "hybrid"

        if complexity >= 4 or intent == QueryIntent.COMPARISON:
            rationale["retrieval"] = (
                f"Complexity {complexity}/5 or comparison query — MMR retrieval "
                "surfaces diverse relevant chunks."
            )
            return "mmr"

        if analysis["is_temporal"]:
            rationale["retrieval"] = (
                "Temporal query — hybrid retrieval captures date/time keywords better."
            )
            return "hybrid"

        rationale["retrieval"] = "Standard factual query — similarity retrieval is sufficient."
        return "similarity"

    def _recommend_reranking(self, analysis: Dict[str, Any]) -> str | None:
        rationale = analysis["rationale"]
        complexity = analysis["complexity"]
        intent = analysis["intent"]

        if complexity >= 4 or analysis["is_multi_hop"]:
            rationale["reranking"] = (
                "High complexity / multi-hop — cross-encoder reranking provides "
                "deep query-passage relevance scoring."
            )
            return "cross_encoder"

        if intent in (QueryIntent.ANALYTICAL, QueryIntent.COMPARISON):
            rationale["reranking"] = (
                f"'{intent.value}' intent — BM25 reranking boosts keyword precision."
            )
            return "bm25"

        rationale["reranking"] = "Low complexity factual query — no reranking needed."
        return None

    def _recommend_template(self, analysis: Dict[str, Any]) -> str:
        mapping = {
            QueryIntent.FACTUAL: "factual_qa",
            QueryIntent.ANALYTICAL: "analysis",
            QueryIntent.COMPARISON: "comparison",
            QueryIntent.CREATIVE: "creative",
        }
        return mapping.get(analysis["intent"], "factual_qa")
