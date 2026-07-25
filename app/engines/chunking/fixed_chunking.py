"""Fixed Character Chunking Strategy"""
from typing import List, Dict, Any
import re


class FixedChunking:
    """Fixed character-based chunking with overlap"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        """
        Initialize fixed chunking strategy
        
        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text into fixed-size chunks with overlap
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to include with each chunk
        
        Returns:
            List of chunks with metadata
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Don't go beyond text length
            if end > len(text):
                end = len(text)
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_metadata = {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_id,
                    "start_char": start,
                    "end_char": end,
                    "chunk_length": len(chunk_text),
                    "chunking_strategy": "fixed",
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                }
                
                if metadata:
                    chunk_metadata.update(metadata)
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })
                chunk_id += 1
            
            # Move start position with overlap
            if end == len(text):
                break
            
            if self.chunk_overlap >= self.chunk_size:
                start = end
            else:
                next_start = end - self.chunk_overlap
                if next_start <= start:
                    start = end
                else:
                    start = next_start
        
        return chunks
    
    def chunk_by_sentences(
        self,
        text: str,
        max_chunk_size: int = 500,
        overlap_sentences: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks by sentences with size limit
        
        Args:
            text: Input text to chunk
            max_chunk_size: Maximum characters per chunk
            overlap_sentences: Number of sentences to overlap
        
        Returns:
            List of chunks with metadata
        """
        # Split by sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_id = 0
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed chunk size
            if current_length + len(sentence) > max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_id,
                        "chunk_length": len(chunk_text),
                        "sentence_count": len(current_chunk),
                        "chunking_strategy": "fixed_sentence",
                        "max_chunk_size": max_chunk_size,
                        "overlap_sentences": overlap_sentences,
                    }
                })
                chunk_id += 1
                
                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - overlap_sentences)
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(s) for s in current_chunk) + len(current_chunk)  # + spaces
            
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_id,
                    "chunk_length": len(chunk_text),
                    "sentence_count": len(current_chunk),
                    "chunking_strategy": "fixed_sentence",
                    "max_chunk_size": max_chunk_size,
                    "overlap_sentences": overlap_sentences,
                }
            })
        
        return chunks
