"""Hybrid Retrieval Strategy (Vector + Keyword)"""
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi
import re


class HybridRetrieval:
    """Hybrid retrieval combining vector search and BM25 keyword search"""
    
    def __init__(self, vector_store):
        """
        Initialize hybrid retrieval
        
        Args:
            vector_store: Vector storage instance
        """
        self.vector_store = vector_store
        self.bm25_index = None
        self.documents = []
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """Build BM25 keyword index from stored documents"""
        try:
            # Get all documents from vector store
            all_docs = self.vector_store.get()
            
            if all_docs and all_docs.get("documents"):
                self.documents = all_docs["documents"]
                # Tokenize documents for BM25
                tokenized_docs = [
                    self._tokenize(doc) for doc in self.documents
                ]
                self.bm25_index = BM25Okapi(tokenized_docs)
        except Exception as e:
            print(f"Warning: Failed to build keyword index: {e}")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Convert to lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens
    
    def retrieve(
        self,
        query_embedding: List[float],
        query_text: str,
        n_results: int = 10,
        alpha: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using hybrid vector + keyword search
        
        Args:
            query_embedding: Query embedding vector
            query_text: Query text for keyword search
            n_results: Number of results to return
            alpha: Weight for vector search (0-1), keyword weight = 1-alpha
            filters: Optional metadata filters
        
        Returns:
            List of retrieved documents with combined scores
        """
        try:
            # Vector search
            vector_results = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results * 2,  # Get more for reranking
                where=filters
            )
            
            # Keyword search
            keyword_scores = {}
            if self.bm25_index and query_text:
                tokenized_query = self._tokenize(query_text)
                doc_scores = self.bm25_index.get_scores(tokenized_query)
                
                # Normalize BM25 scores
                if len(doc_scores) > 0:
                    max_score = max(doc_scores)
                    if max_score > 0:
                        doc_scores = doc_scores / max_score
                
                for i, score in enumerate(doc_scores):
                    keyword_scores[i] = score
            
            # Combine scores
            combined_results = []
            vector_ids = vector_results.get("ids", [])
            
            for i, doc_id in enumerate(vector_ids):
                vector_score = vector_results["distances"][i] if "distances" in vector_results else 0
                
                # Find keyword score for this document
                keyword_score = 0
                if i in keyword_scores:
                    keyword_score = keyword_scores[i]
                
                # Combine scores
                combined_score = alpha * vector_score + (1 - alpha) * keyword_score
                
                combined_results.append({
                    "id": doc_id,
                    "text": vector_results["documents"][i],
                    "metadata": vector_results["metadatas"][i],
                    "vector_score": vector_score,
                    "keyword_score": keyword_score,
                    "combined_score": combined_score,
                    "retrieval_strategy": "hybrid"
                })
            
            # Sort by combined score and return top n
            combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
            return combined_results[:n_results]
            
        except Exception as e:
            raise RuntimeError(f"Hybrid retrieval failed: {e}")
    
    def update_index(self, new_documents: List[str]):
        """
        Update the keyword index with new documents
        
        Args:
            new_documents: List of new document texts
        """
        self.documents.extend(new_documents)
        tokenized_new = [self._tokenize(doc) for doc in new_documents]
        
        # Rebuild index (simpler than incremental update)
        tokenized_all = [self._tokenize(doc) for doc in self.documents]
        self.bm25_index = BM25Okapi(tokenized_all)
