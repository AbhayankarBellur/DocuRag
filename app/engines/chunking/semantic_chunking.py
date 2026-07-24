"""Semantic Chunking Strategy"""
from typing import List, Dict, Any
import re


class SemanticChunking:
    """Semantic chunking using sentence embeddings and boundary detection"""
    
    def __init__(self, embedding_model=None, similarity_threshold: float = 0.7):
        """
        Initialize semantic chunking strategy
        
        Args:
            embedding_model: Optional sentence transformer model
            similarity_threshold: Threshold for semantic similarity
        """
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text into semantically coherent chunks
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to include with each chunk
        
        Returns:
            List of chunks with metadata
        """
        if not text:
            return []
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return []
        
        # If no embedding model, fall back to paragraph-based chunking
        if self.embedding_model is None:
            return self._chunk_by_paragraphs(text, metadata)
        
        # Get embeddings for sentences
        embeddings = self.embedding_model.encode(sentences)
        
        # Group sentences by semantic similarity
        chunks = self._group_by_similarity(sentences, embeddings)
        
        # Add metadata
        chunk_id = 0
        result = []
        for chunk in chunks:
            chunk_text = " ".join(chunk)
            chunk_metadata = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_id,
                "chunk_length": len(chunk_text),
                "sentence_count": len(chunk),
                "chunking_strategy": "semantic",
                "similarity_threshold": self.similarity_threshold,
            }
            
            if metadata:
                chunk_metadata.update(metadata)
            
            result.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
            chunk_id += 1
        
        return result
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _group_by_similarity(
        self,
        sentences: List[str],
        embeddings: List
    ) -> List[List[str]]:
        """Group sentences by semantic similarity"""
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        chunks = []
        current_chunk = [sentences[0]]
        
        for i in range(1, len(sentences)):
            # Calculate similarity with last sentence in current chunk
            last_embedding = embeddings[i - 1].reshape(1, -1)
            current_embedding = embeddings[i].reshape(1, -1)
            similarity = cosine_similarity(last_embedding, current_embedding)[0][0]
            
            if similarity >= self.similarity_threshold:
                current_chunk.append(sentences[i])
            else:
                chunks.append(current_chunk)
                current_chunk = [sentences[i]]
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_by_paragraphs(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Fallback: chunk by paragraphs"""
        paragraphs = re.split(r'\n\n+', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        chunk_id = 0
        
        for paragraph in paragraphs:
            chunk_metadata = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_id,
                "chunk_length": len(paragraph),
                "chunking_strategy": "semantic_fallback_paragraph",
            }
            
            if metadata:
                chunk_metadata.update(metadata)
            
            chunks.append({
                "text": paragraph,
                "metadata": chunk_metadata
            })
            chunk_id += 1
        
        return chunks
