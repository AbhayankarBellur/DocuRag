"""Section-Based Chunking Strategy"""
from typing import List, Dict, Any
import re


class SectionChunking:
    """Section-based chunking using header/paragraph structure"""
    
    def __init__(self, min_section_size: int = 100, merge_small_sections: bool = True):
        """
        Initialize section chunking strategy
        
        Args:
            min_section_size: Minimum characters for a section
            merge_small_sections: Whether to merge small sections with neighbors
        """
        self.min_section_size = min_section_size
        self.merge_small_sections = merge_small_sections
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text into sections based on headers and structure
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to include with each chunk
        
        Returns:
            List of chunks with metadata
        """
        if not text:
            return []
        
        # Detect and split by headers
        sections = self._split_by_headers(text)
        
        # If no headers found, split by paragraphs
        if len(sections) == 1:
            sections = self._split_by_paragraphs(text)
        
        # Merge small sections if enabled
        if self.merge_small_sections:
            sections = self._merge_small_sections(sections)
        
        # Create chunks with metadata
        chunks = []
        chunk_id = 0
        
        for section in sections:
            if not section["content"].strip():
                continue
            
            chunk_metadata = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_id,
                "chunk_length": len(section["content"]),
                "chunking_strategy": "section",
                "section_header": section.get("header", ""),
                "section_level": section.get("level", 0),
            }
            
            if metadata:
                chunk_metadata.update(metadata)
            
            chunks.append({
                "text": section["content"],
                "metadata": chunk_metadata
            })
            chunk_id += 1
        
        return chunks
    
    def _split_by_headers(self, text: str) -> List[Dict[str, str]]:
        """Split text by markdown-style headers"""
        sections = []
        current_section = {"header": "", "level": 0, "content": ""}
        
        lines = text.split('\n')
        
        for line in lines:
            # Check for markdown headers (#, ##, ###)
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                # Save current section if it has content
                if current_section["content"].strip():
                    sections.append(current_section.copy())
                
                # Start new section
                level = len(header_match.group(1))
                header = header_match.group(2)
                current_section = {
                    "header": header,
                    "level": level,
                    "content": line + "\n"
                }
            else:
                current_section["content"] += line + "\n"
        
        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _split_by_paragraphs(self, text: str) -> List[Dict[str, str]]:
        """Split text by paragraphs"""
        paragraphs = re.split(r'\n\n+', text)
        return [
            {"header": "", "level": 0, "content": p.strip()}
            for p in paragraphs if p.strip()
        ]
    
    def _merge_small_sections(
        self,
        sections: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Merge sections that are too small"""
        if not sections:
            return sections
        
        merged = [sections[0]]
        
        for section in sections[1:]:
            last_section = merged[-1]
            
            if len(section["content"]) < self.min_section_size:
                # Merge with previous section
                last_section["content"] += "\n\n" + section["content"]
                # Keep the higher-level header
                if section["level"] > last_section["level"]:
                    last_section["header"] = section["header"]
                    last_section["level"] = section["level"]
            else:
                merged.append(section)
        
        return merged
