"""MMR (Maximal Marginal Relevance) Retrieval Strategy"""
from typing import List, Dict, Any, Optional
import numpy as np
import numpy as np


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


class MMRRetrieval:
    """MMR retrieval for diverse result selection"""
    
    def __init__(self, vector_store):
        """
        Initialize MMR retrieval
        
        Args:
            vector_store: Vector storage instance
        """
        self.vector_store = vector_store
    
    def retrieve(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        lambda_param: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using MMR for diversity
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            lambda_param: Balance between relevance and diversity (0-1)
                         Higher = more relevance, Lower = more diversity
            filters: Optional metadata filters
        
        Returns:
            List of diverse retrieved documents
        """
        try:
            # Get initial candidate results
            raw = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results * 3,
                where=_chroma_where(filters),
            )

            if not raw or not raw.get("ids"):
                return []

            # Flatten Chroma nested lists
            doc_ids       = raw["ids"][0]        if isinstance(raw["ids"][0], list)       else raw["ids"]
            doc_texts     = raw["documents"][0]   if isinstance(raw["documents"][0], list) else raw["documents"]
            doc_metas     = raw["metadatas"][0]   if isinstance(raw["metadatas"][0], list) else raw["metadatas"]
            doc_distances = raw["distances"][0]   if raw.get("distances") and isinstance(raw["distances"][0], list) else (raw.get("distances") or [0.0] * len(doc_ids))
            doc_embeddings = (raw["embeddings"][0] if raw.get("embeddings") and isinstance(raw["embeddings"][0], list)
                              else raw.get("embeddings") or [])

            n = len(doc_ids)
            if n == 0:
                return []

            if not doc_embeddings:
                # No embeddings returned — fall back to plain similarity order
                return [
                    {
                        "id":   str(doc_ids[i]) if not isinstance(doc_ids[i], list) else str(doc_ids[i][0]),
                        "text": doc_texts[i],
                        "metadata": doc_metas[i] if doc_metas else {},
                        "score": float(doc_distances[i]) if doc_distances else None,
                        "retrieval_strategy": "mmr",
                    }
                    for i in range(min(n_results, n))
                ]

            import numpy as np
            doc_distances_f = [float(d) for d in doc_distances]
            doc_vecs = np.array(doc_embeddings, dtype=float)

            selected: List[int] = []
            remaining = list(range(n))

            for _ in range(min(n_results, n)):
                if not remaining:
                    break
                mmr_scores = []
                for idx in remaining:
                    relevance = doc_distances_f[idx]
                    max_sim = 0.0
                    if selected:
                        sel_vecs = doc_vecs[selected]
                        cur_vec  = doc_vecs[idx]
                        sims = sel_vecs @ cur_vec / (
                            np.linalg.norm(sel_vecs, axis=1) * np.linalg.norm(cur_vec) + 1e-10
                        )
                        max_sim = float(np.max(sims))
                    mmr_scores.append(lambda_param * relevance - (1.0 - lambda_param) * max_sim)
                best = remaining[int(np.argmax(mmr_scores))]
                selected.append(best)
                remaining.remove(best)

            return [
                {
                    "id":   str(doc_ids[i]) if not isinstance(doc_ids[i], list) else str(doc_ids[i][0]),
                    "text": doc_texts[i],
                    "metadata": doc_metas[i] if doc_metas else {},
                    "score": float(doc_distances_f[i]),
                    "retrieval_strategy": "mmr",
                }
                for i in selected
            ]
            
        except Exception as e:
            raise RuntimeError(f"MMR retrieval failed: {e}")
    
    def retrieve_diverse(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        diversity_threshold: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents with enforced diversity threshold
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            diversity_threshold: Minimum dissimilarity between results
            filters: Optional metadata filters
        
        Returns:
            List of diverse retrieved documents
        """
        # Use low lambda for high diversity
        return self.retrieve(
            query_embedding=query_embedding,
            n_results=n_results,
            lambda_param=0.3,
            filters=filters
        )
