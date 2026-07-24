"""Recursive Chunking Strategy"""
from typing import List, Dict, Any
import re


class RecursiveChunking:
    """Recursive chunking for hierarchical document structure"""
    
    def __init__(
        self,
        chunk_sizes: List[int] = None,
        chunk_overlaps: List[int] = None,
        separators: List[str] = None
    ):
        """
        Initialize recursive chunking strategy
        
        Args:
            chunk_sizes: List of chunk sizes to try (largest to smallest)
            chunk_overlaps: List of overlaps corresponding to chunk sizes
            separators: List of separators to try (from largest to smallest)
        """
        self.chunk_sizes = chunk_sizes or [2000, 1000, 500]
        self.chunk_overlaps = chunk_overlaps or [200, 100, 50]
        self.separators = separators or [
            "\n\n\n",  # Triple newline
            "\n\n",    # Double newline
            "\n",      # Single newline
            ". ",      # Sentence end
            "! ",      # Exclamation
            "? ",      # Question
            " ",       # Space
            ""         # Character level
        ]
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text recursively using multiple strategies
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to include with each chunk
        
        Returns:
            List of chunks with metadata
        """
        if not text:
            return []
        
        chunks = self._recursive_split(text, 0)
        
        # Add metadata
        chunk_id = 0
        result = []
        for chunk in chunks:
            chunk_metadata = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_id,
                "chunk_length": len(chunk),
                "chunking_strategy": "recursive",
                "chunk_sizes": self.chunk_sizes,
                "separators_count": len(self.separators),
            }
            
            if metadata:
                chunk_metadata.update(metadata)
            
            result.append({
                "text": chunk,
                "metadata": chunk_metadata
            })
            chunk_id += 1
        
        return result
    
    def _recursive_split(
        self,
        text: str,
        level: int
    ) -> List[str]:
        """Recursively split text"""
        if level >= len(self.chunk_sizes):
            return [text]
        
        chunk_size = self.chunk_sizes[level]
        chunk_overlap = self.chunk_overlaps[level]
        
        # Try each separator
        for separator in self.separators:
            if separator:
                splits = text.split(separator)
            else:
                splits = list(text)
            
            # Check if any split is too large
            if any(len(split) > chunk_size for split in splits):
                # Try next separator
                continue
            
            # If all splits are small enough, merge them into chunks
            chunks = self._merge_splits(splits, chunk_size, chunk_overlap)
            
            # Recursively split any chunks that are still too large
            final_chunks = []
            for chunk in chunks:
                if len(chunk) > chunk_size:
                    final_chunks.extend(self._recursive_split(chunk, level + 1))
                else:
                    final_chunks.append(chunk)
            
            return final_chunks
        
        # If no separator worked, try next chunk size
        return self._recursive_split(text, level + 1)
    
    def _merge_splits(
        self,
        splits: List[str],
        chunk_size: int,
        chunk_overlap: int
    ) -> List[str]:
        """Merge splits into chunks of appropriate size"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        for split in splits:
            split_length = len(split)
            
            # Check if adding this split would exceed chunk size
            if current_length + split_length > chunk_size and current_chunk:
                # Save current chunk
                chunk = "".join(current_chunk)
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_length = 0
                overlap_chunk = []
                
                for s in reversed(current_chunk):
                    if overlap_length + len(s) > chunk_overlap:
                        break
                    overlap_chunk.insert(0, s)
                    overlap_length += len(s)
                
                current_chunk = overlap_chunk
                current_length = overlap_length
            
            current_chunk.append(split)
            current_length += split_length
        
        # Add final chunk
        if current_chunk:
            chunk = "".join(current_chunk)
            chunks.append(chunk)
        
        return chunks
