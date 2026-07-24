"""Document Analyzer for Policy Engine"""
from typing import Dict, Any
import re


class DocumentAnalyzer:
    """Analyzes documents to determine optimal processing strategies"""
    
    def __init__(self):
        """Initialize document analyzer"""
        self.domain_keywords = {
            "legal": ["contract", "law", "legal", "statute", "regulation", "court", "judgment"],
            "technical": ["api", "function", "code", "programming", "algorithm", "database", "server"],
            "medical": ["patient", "diagnosis", "treatment", "symptom", "disease", "medical"],
            "financial": ["stock", "investment", "portfolio", "market", "trading", "financial"],
            "academic": ["research", "study", "paper", "journal", "citation", "abstract"],
        }
    
    def analyze(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze document content and metadata
        
        Args:
            content: Document text content
            metadata: Document metadata from ingestion
        
        Returns:
            Analysis results including recommended strategies
        """
        analysis = {
            "domain": self._classify_domain(content),
            "complexity": self._assess_complexity(content),
            "structure": self._analyze_structure(content),
            "language": self._detect_language(content),
            "recommended_chunking": None,
            "recommended_embedding": None,
            "recommended_retrieval": None,
        }
        
        # Determine recommended strategies
        analysis["recommended_chunking"] = self._recommend_chunking(analysis)
        analysis["recommended_embedding"] = self._recommend_embedding(analysis)
        analysis["recommended_retrieval"] = self._recommend_retrieval(analysis)
        
        return analysis
    
    def _classify_domain(self, content: str) -> str:
        """Classify document domain"""
        content_lower = content.lower()
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return "general"
    
    def _assess_complexity(self, content: str) -> int:
        """Assess document complexity (1-5)"""
        words = content.split()
        if not words:
            return 1
        
        # Average word length
        avg_word_len = sum(len(w) for w in words) / len(words)
        
        # Sentence count
        sentences = len(re.split(r'[.!?]+', content))
        avg_sentence_len = len(words) / max(sentences, 1)
        
        # Technical terms
        technical_indicators = ["algorithm", "implementation", "architecture", "framework"]
        tech_score = sum(1 for ind in technical_indicators if ind in content.lower())
        
        complexity = 1
        if avg_word_len > 5:
            complexity += 1
        if avg_sentence_len > 20:
            complexity += 1
        if tech_score > 0:
            complexity += 1
        
        return min(complexity, 5)
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure"""
        return {
            "has_headers": bool(re.search(r'^#{1,6}\s', content, re.MULTILINE)),
            "has_lists": bool(re.search(r'^\s*[-*+]\s', content, re.MULTILINE)),
            "has_code": bool(re.search(r'```|def |class |function ', content)),
            "has_tables": "|" in content or "table" in content.lower(),
            "paragraph_count": len(re.split(r'\n\n+', content)),
        }
    
    def _detect_language(self, content: str) -> str:
        """Simple language detection"""
        # This is a simplified version - in production, use langdetect
        if not content:
            return "en"
        
        # Check for common non-English patterns
        if re.search(r'[\u4e00-\u9fff]', content):  # Chinese
            return "zh"
        elif re.search(r'[\u0600-\u06ff]', content):  # Arabic
            return "ar"
        elif re.search(r'[\u0400-\u04ff]', content):  # Russian
            return "ru"
        
        return "en"
    
    def _recommend_chunking(self, analysis: Dict[str, Any]) -> str:
        """Recommend chunking strategy based on analysis"""
        if analysis["structure"]["has_headers"]:
            return "section"
        elif analysis["complexity"] >= 4:
            return "semantic"
        elif analysis["domain"] in ["legal", "technical"]:
            return "recursive"
        else:
            return "fixed"
    
    def _recommend_embedding(self, analysis: Dict[str, Any]) -> str:
        """Recommend embedding model based on analysis"""
        if analysis["complexity"] >= 4:
            return "BAAI/bge-large-en-v1.5"
        elif analysis["complexity"] >= 3:
            return "BAAI/bge-base-en-v1.5"
        else:
            return "BAAI/bge-small-en-v1.5"
    
    def _recommend_retrieval(self, analysis: Dict[str, Any]) -> str:
        """Recommend retrieval strategy based on analysis"""
        if analysis["domain"] == "technical":
            return "hybrid"
        elif analysis["complexity"] >= 4:
            return "mmr"
        else:
            return "similarity"
