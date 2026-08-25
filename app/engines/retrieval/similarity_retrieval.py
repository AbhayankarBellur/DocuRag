"""Similarity-based Retrieval Strategy"""
from typing import List, Dict, Any, Optional


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


class SimilarityRetrieval:
    """Similarity-based retrieval using vector search"""
    
    def __init__(self, vector_store):
        """
        Initialize similarity retrieval
        
        Args:
            vector_store: Vector storage instance (Chroma, Qdrant, or FAISS)
        """
        self.vector_store = vector_store
    
    def retrieve(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar documents using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            filters: Optional metadata filters
        
        Returns:
            List of retrieved documents with scores
        """
        try:
            results = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results,
                where=_chroma_where(filters)
            )

            # Flatten Chroma's nested lists
            formatted_results = []
            ids       = results.get("ids", [[]])
            documents = results.get("documents", [[]])
            metadatas = results.get("metadatas", [[]])
            distances = results.get("distances", [[]])

            # Chroma always returns nested lists — unwrap
            if ids and isinstance(ids[0], list):
                ids       = ids[0]
                documents = documents[0]
                metadatas = metadatas[0] if metadatas else []
                distances = distances[0] if distances else []

            for i in range(len(ids)):
                doc_id = ids[i]
                # Guard: ensure id is a plain string
                if isinstance(doc_id, list):
                    doc_id = doc_id[0]
                formatted_results.append({
                    "id":       str(doc_id),
                    "text":     documents[i],
                    "metadata": metadatas[i] if metadatas else {},
                    "score":    float(distances[i]) if distances else None,
                    "retrieval_strategy": "similarity",
                })

            return formatted_results
        except Exception as e:
            raise RuntimeError(f"Similarity retrieval failed: {e}")
    
    def retrieve_with_threshold(
        self,
        query_embedding: List[float],
        threshold: float = 0.7,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents above a similarity threshold
        
        Args:
            query_embedding: Query embedding vector
            threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results to return
            filters: Optional metadata filters
        
        Returns:
            List of retrieved documents above threshold
        """
        results = self.retrieve(
            query_embedding=query_embedding,
            n_results=max_results,
            filters=filters
        )
        
        # Filter by threshold (assuming cosine similarity)
        filtered_results = [
            r for r in results
            if r["score"] is not None and r["score"] >= threshold
        ]
        
        return filtered_results
