"""Document Analyzer for Policy Engine"""
from typing import Dict, Any
import re


class DocumentAnalyzer:
    """Analyzes documents to determine optimal processing strategies."""

    domain_keywords: Dict[str, list] = {
        "legal": [
            "contract", "law", "legal", "statute", "regulation", "court",
            "judgment", "clause", "liability", "indemnity", "jurisdiction",
        ],
        "technical": [
            "api", "function", "code", "programming", "algorithm", "database",
            "server", "endpoint", "class", "module", "framework", "sdk",
            "repository", "deployment", "pipeline", "runtime",
        ],
        "medical": [
            "patient", "diagnosis", "treatment", "symptom", "disease",
            "medical", "clinical", "therapy", "dosage", "pathology",
            "prognosis", "surgery", "prescription",
        ],
        "financial": [
            "stock", "investment", "portfolio", "market", "trading",
            "financial", "revenue", "equity", "dividend", "hedge",
            "bond", "fiscal", "balance sheet", "cash flow",
        ],
        "academic": [
            "research", "study", "paper", "journal", "citation",
            "abstract", "hypothesis", "methodology", "literature review",
            "experiment", "peer-reviewed", "findings",
        ],
    }

    def analyze(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze document content and metadata.

        Returns a dict with all signals plus recommended strategies.
        """
        structure = self._analyze_structure(content)
        complexity = self._assess_complexity(content)
        domain = self._classify_domain(content)
        language = self._detect_language(content)

        # Extra signals
        word_count = len(content.split())
        avg_sentence_length = self._avg_sentence_length(content)
        content_type = self._infer_content_type(structure, content)

        analysis: Dict[str, Any] = {
            "domain": domain,
            "complexity": complexity,
            "structure": structure,
            "language": language,
            "word_count": word_count,
            "avg_sentence_length": avg_sentence_length,
            "content_type": content_type,   # prose | structured | code | mixed
            "recommended_chunking": None,
            "recommended_embedding": None,
            "recommended_retrieval": None,
            "rationale": {},
        }

        analysis["recommended_chunking"] = self._recommend_chunking(analysis)
        analysis["recommended_embedding"] = self._recommend_embedding(analysis)
        analysis["recommended_retrieval"] = self._recommend_retrieval(analysis)

        return analysis

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def _classify_domain(self, content: str) -> str:
        content_lower = content.lower()
        scores = {
            domain: sum(1 for kw in kws if kw in content_lower)
            for domain, kws in self.domain_keywords.items()
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "general"

    def _assess_complexity(self, content: str) -> int:
        words = content.split()
        if not words:
            return 1

        avg_word_len = sum(len(w) for w in words) / len(words)
        avg_sent_len = self._avg_sentence_length(content)

        technical_indicators = [
            "algorithm", "implementation", "architecture",
            "framework", "methodology", "theorem", "hypothesis",
        ]
        tech_score = sum(1 for ind in technical_indicators if ind in content.lower())

        complexity = 1
        if avg_word_len > 5.5:
            complexity += 1
        if avg_sent_len > 22:
            complexity += 1
        if tech_score >= 2:
            complexity += 1
        if len(words) > 3000:
            complexity += 1

        return min(complexity, 5)

    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        has_headers = bool(re.search(r"^#{1,6}\s", content, re.MULTILINE))
        has_lists = bool(re.search(r"^\s*[-*+\d]\.", content, re.MULTILINE))
        has_code = bool(re.search(r"```|def |class |function |import ", content))
        has_tables = "|" in content and content.count("|") > 4
        paragraph_count = len([p for p in re.split(r"\n\n+", content) if p.strip()])
        has_numbered_sections = bool(
            re.search(r"^\s*\d+[\.\)]\s+\w", content, re.MULTILINE)
        )
        return {
            "has_headers": has_headers,
            "has_lists": has_lists,
            "has_code": has_code,
            "has_tables": has_tables,
            "paragraph_count": paragraph_count,
            "has_numbered_sections": has_numbered_sections,
        }

    def _infer_content_type(self, structure: Dict[str, Any], content: str) -> str:
        if structure["has_code"] and content.count("```") > 2:
            return "code"
        if structure["has_headers"] or structure["has_numbered_sections"]:
            return "structured"
        # Mostly short paragraphs ≈ prose
        return "prose"

    def _avg_sentence_length(self, content: str) -> float:
        words = content.split()
        sentences = max(len(re.split(r"[.!?]+", content)), 1)
        return len(words) / sentences

    def _detect_language(self, content: str) -> str:
        if re.search(r"[\u4e00-\u9fff]", content):
            return "zh"
        if re.search(r"[\u0600-\u06ff]", content):
            return "ar"
        if re.search(r"[\u0400-\u04ff]", content):
            return "ru"
        return "en"

    # ------------------------------------------------------------------
    # Recommendation helpers  (also fill rationale)
    # ------------------------------------------------------------------

    def _recommend_chunking(self, analysis: Dict[str, Any]) -> str:
        s = analysis["structure"]
        rationale = analysis["rationale"]

        if s["has_headers"] or s["has_numbered_sections"]:
            rationale["chunking"] = (
                "Document has clear section headers — section chunking preserves "
                "logical boundaries."
            )
            return "section"

        if analysis["content_type"] == "code":
            rationale["chunking"] = (
                "Document is code-heavy — recursive chunking respects code block "
                "boundaries."
            )
            return "recursive"

        if analysis["complexity"] >= 4 or analysis["domain"] in ("academic", "legal"):
            rationale["chunking"] = (
                f"High complexity ({analysis['complexity']}/5) or domain "
                f"'{analysis['domain']}' — semantic chunking groups by meaning."
            )
            return "semantic"

        if analysis["domain"] == "technical":
            rationale["chunking"] = (
                "Technical domain — recursive chunking handles nested structures well."
            )
            return "recursive"

        rationale["chunking"] = "General document — fixed-size chunking is fast and reliable."
        return "fixed"

    def _recommend_embedding(self, analysis: Dict[str, Any]) -> str:
        rationale = analysis["rationale"]
        complexity = analysis["complexity"]

        if complexity >= 4:
            rationale["embedding"] = (
                f"Complexity {complexity}/5 → large BGE model for richer representations."
            )
            return "BAAI/bge-large-en-v1.5"

        if complexity >= 3 or analysis["domain"] in ("academic", "legal", "medical"):
            rationale["embedding"] = (
                f"Complexity {complexity}/5 or specialised domain "
                f"'{analysis['domain']}' → base BGE model."
            )
            return "BAAI/bge-base-en-v1.5"

        rationale["embedding"] = "Low complexity — small BGE model is fast and sufficient."
        return "BAAI/bge-small-en-v1.5"

    def _recommend_retrieval(self, analysis: Dict[str, Any]) -> str:
        rationale = analysis["rationale"]

        if analysis["domain"] == "technical" or analysis["structure"]["has_code"]:
            rationale["retrieval"] = (
                "Technical/code content benefits from keyword + vector hybrid retrieval."
            )
            return "hybrid"

        if analysis["complexity"] >= 4:
            rationale["retrieval"] = (
                "High complexity — MMR retrieval provides diverse, non-redundant results."
            )
            return "mmr"

        rationale["retrieval"] = "Standard similarity retrieval is sufficient."
        return "similarity"
