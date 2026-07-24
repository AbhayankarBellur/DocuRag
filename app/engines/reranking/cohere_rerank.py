"""Cohere Re-ranking Strategy"""
from typing import List, Dict, Any
import cohere
from app.utils.config import settings


class CohereRerank:
    """Cohere API-based neural re-ranking"""
    
    def __init__(self, api_key: str = None, model: str = "rerank-english-v2.0"):
        """
        Initialize Cohere reranker
        
        Args:
            api_key: Cohere API key
            model: Cohere rerank model
        """
        self.api_key = api_key or settings.cohere_api_key
        self.model = model
        
        if not self.api_key:
            raise ValueError("Cohere API key is required")
        
        self.client = cohere.Client(self.api_key)
    
    def rerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results using Cohere API
        
        Args:
            results: Initial retrieval results
            query: Query text
            top_k: Number of top results to return
        
        Returns:
            Re-ranked results
        """
        if not results:
            return results
        
        if top_k is None:
            top_k = len(results)
        
        # Extract documents and IDs
        documents = [r["text"] for r in results]
        
        try:
            # Call Cohere rerank API
            response = self.client.rerank(
                query=query,
                documents=documents,
                top_n=top_k,
                model=self.model
            )
            
            # Get reranked indices and scores
            reranked_results = []
            for result in response.results:
                original_idx = result.index
                original_result = results[original_idx].copy()
                original_result["cohere_score"] = result.relevance_score
                reranked_results.append(original_result)
            
            return reranked_results
            
        except Exception as e:
            raise RuntimeError(f"Cohere reranking failed: {e}")
    
    def get_rerank_info(self) -> Dict[str, Any]:
        """Get reranker information"""
        return {
            "type": "cohere",
            "model": self.model,
            "description": "Cohere neural re-ranking"
        }
