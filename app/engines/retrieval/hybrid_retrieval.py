"""Hybrid Retrieval Strategy (Vector + Keyword)"""
from typing import List, Dict, Any, Optional
import re


def _chroma_where(filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert a plain filter dict to Chroma's $and syntax when needed."""
    if not filters:
        return None
    items = {k: v for k, v in filters.items() if v is not None}
    if not items:
        return None
    if len(items) == 1:
        return items
    return {"$and": [{k: v} for k, v in items.items()]}


class HybridRetrieval:
    """Hybrid retrieval combining vector search and BM25 keyword search."""

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.bm25_index = None
        self._doc_ids: List[str] = []     # parallel list of doc IDs for BM25 index
        self._build_keyword_index()

    def _build_keyword_index(self):
        try:
            from rank_bm25 import BM25Okapi
            all_docs = self.vector_store.get()
            if not all_docs or not all_docs.get("documents"):
                return

            # Chroma returns nested lists — flatten
            raw_docs = all_docs["documents"]
            raw_ids  = all_docs.get("ids", [])
            if raw_docs and isinstance(raw_docs[0], list):
                raw_docs = raw_docs[0]
                raw_ids  = raw_ids[0] if raw_ids else []

            self._doc_ids = raw_ids
            tokenized = [self._tokenize(d) for d in raw_docs]
            self.bm25_index = BM25Okapi(tokenized)
        except Exception as e:
            print(f"WARNING: Failed to build keyword index: {e}", flush=True)

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def retrieve(
        self,
        query_embedding: List[float],
        query_text: str,
        n_results: int = 10,
        alpha: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            # ── 1. Vector search ───────────────────────────────────────
            raw = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results * 2,
                where=_chroma_where(filters),
            )

            # Flatten Chroma's nested lists
            ids       = raw.get("ids", [[]])[0]       if raw.get("ids")       else []
            docs      = raw.get("documents", [[]])[0]  if raw.get("documents") else []
            metas     = raw.get("metadatas", [[]])[0]  if raw.get("metadatas") else []
            distances = raw.get("distances", [[]])[0]  if raw.get("distances") else [0.0] * len(ids)

            if not ids:
                return []

            # ── 2. BM25 keyword scores keyed by doc ID ────────────────
            bm25_by_id: Dict[str, float] = {}
            if self.bm25_index and query_text and self._doc_ids:
                scores = self.bm25_index.get_scores(self._tokenize(query_text))
                max_s = float(max(scores)) if len(scores) > 0 else 0.0
                if max_s > 0:
                    scores = scores / max_s
                for doc_id, score in zip(self._doc_ids, scores):
                    bm25_by_id[doc_id] = float(score)

            # ── 3. Combine ─────────────────────────────────────────────
            results = []
            for i, doc_id in enumerate(ids):
                # Ensure doc_id is a plain string, not a list
                if isinstance(doc_id, list):
                    doc_id = doc_id[0]
                vec_score  = float(distances[i]) if distances else 0.0
                kw_score   = bm25_by_id.get(str(doc_id), 0.0)
                combined   = alpha * vec_score + (1.0 - alpha) * kw_score
                results.append({
                    "id":               str(doc_id),
                    "text":             docs[i],
                    "metadata":         metas[i] if metas else {},
                    "score":            vec_score,
                    "keyword_score":    kw_score,
                    "combined_score":   combined,
                    "retrieval_strategy": "hybrid",
                })

            results.sort(key=lambda x: x["combined_score"], reverse=True)
            return results[:n_results]

        except Exception as e:
            raise RuntimeError(f"Hybrid retrieval failed: {e}")

    def update_index(self, new_documents: List[str]):
        """Rebuild BM25 index after adding new documents."""
        self._build_keyword_index()
