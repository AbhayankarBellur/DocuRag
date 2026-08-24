"""Policy Domain Models — typed workflow configuration"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Strategy option enumerations
# ---------------------------------------------------------------------------

class StrategyMode(str, Enum):
    """Controls whether a strategy was user-supplied or auto-selected."""
    AUTO = "auto"
    MANUAL = "manual"


class ChunkingStrategy(str, Enum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    SECTION = "section"
    AUTO = "auto"


class EmbeddingModel(str, Enum):
    BGE_SMALL = "BAAI/bge-small-en-v1.5"
    BGE_BASE = "BAAI/bge-base-en-v1.5"
    BGE_LARGE = "BAAI/bge-large-en-v1.5"
    AUTO = "auto"


class RetrievalStrategy(str, Enum):
    SIMILARITY = "similarity"
    HYBRID = "hybrid"
    MMR = "mmr"
    AUTO = "auto"


class RerankingStrategy(str, Enum):
    BM25 = "bm25"
    CROSS_ENCODER = "cross_encoder"
    COHERE = "cohere"
    NONE = "none"
    AUTO = "auto"


class PromptTemplate(str, Enum):
    FACTUAL_QA = "factual_qa"
    ANALYSIS = "analysis"
    COMPARISON = "comparison"
    CREATIVE = "creative"
    AUTO = "auto"


# ---------------------------------------------------------------------------
# Resolved workflow — produced by PolicyEngine after all overrides applied
# ---------------------------------------------------------------------------

@dataclass
class WorkflowConfig:
    """
    Fully resolved workflow configuration.

    Fields ending in ``_mode`` indicate whether the corresponding strategy was
    auto-selected (AUTO) or explicitly supplied by the caller (MANUAL).
    """

    # --- chunking ---
    chunking_strategy: str = "fixed"
    chunking_mode: StrategyMode = StrategyMode.AUTO

    # --- embedding ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_mode: StrategyMode = StrategyMode.AUTO

    # --- retrieval ---
    retrieval_strategy: str = "similarity"
    retrieval_mode: StrategyMode = StrategyMode.AUTO

    # --- reranking ---
    reranking_strategy: Optional[str] = None   # None means disabled
    reranking_mode: StrategyMode = StrategyMode.AUTO

    # --- generation ---
    prompt_template: str = "factual_qa"
    prompt_mode: StrategyMode = StrategyMode.AUTO
    generation_params: Dict[str, Any] = field(default_factory=lambda: {
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
    })

    # --- diagnostics (auto-filled by engine) ---
    auto_rationale: Dict[str, str] = field(default_factory=dict)
    """Human-readable explanation for each auto-selected strategy."""

    document_domain: Optional[str] = None
    document_complexity: Optional[int] = None
    query_intent: Optional[str] = None
    query_complexity: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict (suitable for JSON response)."""
        return {
            "chunking_strategy": self.chunking_strategy,
            "chunking_mode": self.chunking_mode.value,
            "embedding_model": self.embedding_model,
            "embedding_mode": self.embedding_mode.value,
            "retrieval_strategy": self.retrieval_strategy,
            "retrieval_mode": self.retrieval_mode.value,
            "reranking_strategy": self.reranking_strategy,
            "reranking_mode": self.reranking_mode.value,
            "prompt_template": self.prompt_template,
            "prompt_mode": self.prompt_mode.value,
            "generation_params": self.generation_params,
            "auto_rationale": self.auto_rationale,
            "document_domain": self.document_domain,
            "document_complexity": self.document_complexity,
            "query_intent": self.query_intent,
            "query_complexity": self.query_complexity,
        }
