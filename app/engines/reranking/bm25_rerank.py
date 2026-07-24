"""BM25 Re-ranking Strategy"""
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import re


class BM25Rerank:
    """BM25-based re-ranking for retrieval results"""
    
    def __init__(self):
        """Initialize BM25 reranker"""
        self.bm25_index = None
        self.documents = []
    
    def rerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results using BM25
        
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
        
        # Extract documents
        documents = [r["text"] for r in results]
        
        # Tokenize documents
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        
        # Build BM25 index
        self.bm25_index = BM25Okapi(tokenized_docs)
        
        # Get BM25 scores for query
        tokenized_query = self._tokenize(query)
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # Add BM25 scores to results
        for i, result in enumerate(results):
            result["bm25_score"] = float(scores[i])
        
        # Sort by BM25 score
        reranked = sorted(results, key=lambda x: x["bm25_score"], reverse=True)
        
        return reranked[:top_k]
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens
    
    def get_rerank_info(self) -> Dict[str, Any]:
        """Get reranker information"""
        return {
            "type": "bm25",
            "description": "BM25 keyword-based re-ranking"
        }
