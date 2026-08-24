"""
Engine Registry
---------------
Single source of truth for engine instantiation.

Both DocumentService and QueryService import from here so each engine class
is only ever instantiated once (lazy singleton per key).  Retrieval engines
take the vector-store instance as an argument, so they are keyed by
``(strategy, vector_store_id)``.
"""
from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.engines.storage.chroma_storage import ChromaStorage


# ---------------------------------------------------------------------------
# Available strategy names (authoritative lists used by the policy API)
# ---------------------------------------------------------------------------

CHUNKING_STRATEGIES = ["fixed", "recursive", "semantic", "section"]
EMBEDDING_MODELS = [
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5",
    "BAAI/bge-large-en-v1.5",
]
RETRIEVAL_STRATEGIES = ["similarity", "hybrid", "mmr"]
RERANKING_STRATEGIES = ["bm25", "cross_encoder", "cohere"]
VECTOR_STORES = ["chroma"]  # faiss / qdrant can be added here


class EngineRegistry:
    """
    Lazy singleton registry for all pipeline engines.

    Usage::

        registry = EngineRegistry()

        # embedding
        embedder = registry.get_embedding("BAAI/bge-small-en-v1.5")

        # vector store
        store = registry.get_vector_store("chroma")

        # retrieval (needs the store)
        retriever = registry.get_retrieval("hybrid", store)

        # reranking (optional)
        reranker = registry.get_reranking("bm25")   # None if strategy is "none"

        # chunking
        chunker = registry.get_chunking("fixed")
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._chunking: Dict[str, Any] = {}
        self._embedding: Dict[str, Any] = {}
        self._retrieval: Dict[str, Any] = {}
        self._reranking: Dict[str, Any] = {}
        self._vector_store: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def get_chunking(self, strategy: str) -> Any:
        """Return a chunking engine for the given strategy name."""
        strategy = strategy.lower()
        if strategy not in CHUNKING_STRATEGIES:
            raise ValueError(
                f"Unknown chunking strategy '{strategy}'. "
                f"Valid options: {CHUNKING_STRATEGIES}"
            )
        with self._lock:
            if strategy not in self._chunking:
                self._chunking[strategy] = self._build_chunking(strategy)
        return self._chunking[strategy]

    def _build_chunking(self, strategy: str) -> Any:
        if strategy == "fixed":
            from app.engines.chunking.fixed_chunking import FixedChunking
            return FixedChunking()
        if strategy == "recursive":
            from app.engines.chunking.recursive_chunking import RecursiveChunking
            return RecursiveChunking()
        if strategy == "semantic":
            from app.engines.chunking.semantic_chunking import SemanticChunking
            return SemanticChunking()
        if strategy == "section":
            from app.engines.chunking.section_chunking import SectionChunking
            return SectionChunking()
        raise ValueError(f"No builder for chunking strategy '{strategy}'")

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def get_embedding(self, model_name: str) -> Any:
        """Return a BGEEmbedding instance for the given model name."""
        with self._lock:
            if model_name not in self._embedding:
                self._embedding[model_name] = self._build_embedding(model_name)
        return self._embedding[model_name]

    def _build_embedding(self, model_name: str) -> Any:
        # Currently all supported embedding models are BGE variants
        from app.engines.embedding.bge_embedding import BGEEmbedding
        return BGEEmbedding(model_name=model_name)

    # ------------------------------------------------------------------
    # Vector Store
    # ------------------------------------------------------------------

    def get_vector_store(self, store_type: str = "chroma") -> Any:
        """Return a vector store instance."""
        store_type = store_type.lower()
        with self._lock:
            if store_type not in self._vector_store:
                self._vector_store[store_type] = self._build_vector_store(store_type)
        return self._vector_store[store_type]

    def _build_vector_store(self, store_type: str) -> Any:
        if store_type == "chroma":
            from app.engines.storage.chroma_storage import ChromaStorage
            return ChromaStorage()
        if store_type == "faiss":
            from app.engines.storage.faiss_storage import FAISSStorage
            return FAISSStorage()
        if store_type == "qdrant":
            from app.engines.storage.qdrant_storage import QdrantStorage
            return QdrantStorage()
        raise ValueError(f"Unknown vector store '{store_type}'")

    # ------------------------------------------------------------------
    # Retrieval  (keyed by strategy + store id so different stores can coexist)
    # ------------------------------------------------------------------

    def get_retrieval(self, strategy: str, vector_store: Any) -> Any:
        """Return a retrieval engine bound to the given vector store."""
        strategy = strategy.lower()
        if strategy not in RETRIEVAL_STRATEGIES:
            raise ValueError(
                f"Unknown retrieval strategy '{strategy}'. "
                f"Valid options: {RETRIEVAL_STRATEGIES}"
            )
        cache_key = f"{strategy}:{id(vector_store)}"
        with self._lock:
            if cache_key not in self._retrieval:
                self._retrieval[cache_key] = self._build_retrieval(strategy, vector_store)
        return self._retrieval[cache_key]

    def _build_retrieval(self, strategy: str, vector_store: Any) -> Any:
        if strategy == "similarity":
            from app.engines.retrieval.similarity_retrieval import SimilarityRetrieval
            return SimilarityRetrieval(vector_store)
        if strategy == "hybrid":
            from app.engines.retrieval.hybrid_retrieval import HybridRetrieval
            return HybridRetrieval(vector_store)
        if strategy == "mmr":
            from app.engines.retrieval.mmr_retrieval import MMRRetrieval
            return MMRRetrieval(vector_store)
        raise ValueError(f"No builder for retrieval strategy '{strategy}'")

    # ------------------------------------------------------------------
    # Reranking  (None-safe: returns None when strategy is "none"/None)
    # ------------------------------------------------------------------

    def get_reranking(self, strategy: Optional[str]) -> Optional[Any]:
        """
        Return a reranking engine or ``None`` if reranking is disabled.

        Passing ``None``, ``"none"``, or ``""`` all mean *no reranking*.
        ``"cohere"`` will only succeed when a Cohere API key is configured.
        """
        if not strategy or strategy.lower() in ("none", "null", ""):
            return None

        strategy = strategy.lower()
        if strategy not in RERANKING_STRATEGIES:
            raise ValueError(
                f"Unknown reranking strategy '{strategy}'. "
                f"Valid options: {RERANKING_STRATEGIES + ['none']}"
            )
        with self._lock:
            if strategy not in self._reranking:
                self._reranking[strategy] = self._build_reranking(strategy)
        return self._reranking[strategy]

    def _build_reranking(self, strategy: str) -> Any:
        if strategy == "bm25":
            from app.engines.reranking.bm25_rerank import BM25Rerank
            return BM25Rerank()
        if strategy == "cross_encoder":
            from app.engines.reranking.cross_encoder_rerank import CrossEncoderRerank
            return CrossEncoderRerank()
        if strategy == "cohere":
            from app.engines.reranking.cohere_rerank import CohereRerank
            return CohereRerank()
        raise ValueError(f"No builder for reranking strategy '{strategy}'")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def available_options() -> Dict[str, list]:
        """Return all strategy option lists — used by the /api/policy/options endpoint."""
        return {
            "chunking_strategies": CHUNKING_STRATEGIES,
            "embedding_models": EMBEDDING_MODELS,
            "retrieval_strategies": RETRIEVAL_STRATEGIES,
            "reranking_strategies": RERANKING_STRATEGIES + ["none"],
            "vector_stores": VECTOR_STORES,
        }


# Module-level singleton shared across the application
_registry: Optional[EngineRegistry] = None
_registry_lock = Lock()


def get_registry() -> EngineRegistry:
    """Return the application-wide EngineRegistry singleton."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = EngineRegistry()
    return _registry
