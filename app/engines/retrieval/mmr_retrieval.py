"""MMR (Maximal Marginal Relevance) Retrieval Strategy"""
from typing import List, Dict, Any, Optional
import numpy as np


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
            candidates = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results * 3,  # Get more candidates
                where=filters
            )
            
            if not candidates or not candidates.get("ids"):
                return []
            
            # Extract data
            doc_ids = candidates["ids"]
            doc_texts = candidates["documents"]
            doc_embeddings = candidates.get("embeddings", [])
            doc_scores = candidates.get("distances", [0] * len(doc_ids))
            
            if not doc_embeddings:
                # Fallback if embeddings not available
                return [
                    {
                        "id": doc_ids[i],
                        "text": doc_texts[i],
                        "metadata": candidates["metadatas"][i],
                        "score": doc_scores[i],
                        "retrieval_strategy": "mmr"
                    }
                    for i in range(min(n_results, len(doc_ids)))
                ]
            
            # MMR algorithm
            selected_indices = []
            remaining_indices = list(range(len(doc_ids)))
            
            query_vec = np.array(query_embedding).reshape(1, -1)
            doc_vecs = np.array(doc_embeddings)
            
            for _ in range(min(n_results, len(doc_ids))):
                if not remaining_indices:
                    break
                
                mmr_scores = []
                
                for idx in remaining_indices:
                    # Relevance to query
                    relevance = doc_scores[idx]
                    
                    # Diversity from already selected
                    max_similarity = 0
                    if selected_indices:
                        selected_vec = doc_vecs[selected_indices].reshape(-1, 1)
                        current_vec = doc_vecs[idx].reshape(1, -1)
                        similarities = np.dot(selected_vec.T, current_vec.T)
                        max_similarity = np.max(similarities)
                    
                    # MMR score
                    mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                    mmr_scores.append(mmr_score)
                
                # Select document with highest MMR score
                best_idx = remaining_indices[np.argmax(mmr_scores)]
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
            
            # Format results
            results = []
            for idx in selected_indices:
                results.append({
                    "id": doc_ids[idx],
                    "text": doc_texts[idx],
                    "metadata": candidates["metadatas"][idx],
                    "score": doc_scores[idx],
                    "mmr_score": mmr_scores[selected_indices.index(idx)],
                    "retrieval_strategy": "mmr"
                })
            
            return results
            
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
