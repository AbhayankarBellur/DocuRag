"""Engine Tests"""
import pytest
from app.engines.chunking.fixed_chunking import FixedChunking
from app.engines.chunking.semantic_chunking import SemanticChunking
from app.engines.chunking.section_chunking import SectionChunking
from app.engines.chunking.recursive_chunking import RecursiveChunking


def test_fixed_chunking():
    """Test fixed character chunking"""
    chunker = FixedChunking(chunk_size=100, chunk_overlap=20)
    text = "A" * 300
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 1
    assert all("text" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)


def test_section_chunking():
    """Test section-based chunking"""
    chunker = SectionChunking()
    text = """# Header 1
Some content here.

## Header 2
More content.

# Header 3
Final content."""
    
    chunks = chunker.chunk(text)
    assert len(chunks) >= 1
    assert all("text" in chunk for chunk in chunks)


def test_recursive_chunking():
    """Test recursive chunking"""
    chunker = RecursiveChunking()
    text = "A" * 500
    chunks = chunker.chunk(text)
    
    assert len(chunks) >= 1
    assert all("text" in chunk for chunk in chunks)


def test_chunking_metadata():
    """Test chunking metadata"""
    chunker = FixedChunking(chunk_size=50, chunk_overlap=10)
    text = "Test text for chunking with metadata"
    chunks = chunker.chunk(text)
    
    for chunk in chunks:
        assert "chunk_id" in chunk["metadata"]
        assert "chunking_strategy" in chunk["metadata"]
        assert chunk["metadata"]["chunking_strategy"] == "fixed"
