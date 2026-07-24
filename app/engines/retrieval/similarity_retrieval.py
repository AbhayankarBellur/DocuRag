"""Similarity-based Retrieval Strategy"""
from typing import List, Dict, Any, Optional
import numpy as np


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
                where=filters
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results.get("ids", []))):
                formatted_results.append({
                    "id": results["ids"][i],
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "score": results["distances"][i] if "distances" in results else None,
                    "retrieval_strategy": "similarity"
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
