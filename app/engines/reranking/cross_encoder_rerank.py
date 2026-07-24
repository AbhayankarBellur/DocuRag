"""Cross-Encoder Re-ranking Strategy"""
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
import torch


class CrossEncoderRerank:
    """Cross-Encoder-based re-ranking using sentence-transformers"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize Cross-Encoder reranker
        
        Args:
            model_name: Cross-encoder model name
        """
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model"""
        try:
            self.model = CrossEncoder(self.model_name, device=self.device)
        except Exception as e:
            raise RuntimeError(f"Failed to load cross-encoder model: {e}")
    
    def rerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results using cross-encoder
        
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
        
        if self.model is None:
            self._load_model()
        
        # Prepare query-document pairs
        documents = [r["text"] for r in results]
        pairs = [[query, doc] for doc in documents]
        
        try:
            # Get cross-encoder scores
            scores = self.model.predict(pairs)
            
            # Add scores to results
            for i, result in enumerate(results):
                result["cross_encoder_score"] = float(scores[i])
            
            # Sort by cross-encoder score
            reranked = sorted(results, key=lambda x: x["cross_encoder_score"], reverse=True)
            
            return reranked[:top_k]
            
        except Exception as e:
            raise RuntimeError(f"Cross-encoder reranking failed: {e}")
    
    def get_rerank_info(self) -> Dict[str, Any]:
        """Get reranker information"""
        return {
            "type": "cross_encoder",
            "model": self.model_name,
            "device": self.device,
            "description": "Cross-encoder neural re-ranking"
        }
