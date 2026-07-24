"""Query Analyzer for Policy Engine"""
from typing import Dict, Any
import re
from app.models.query import QueryIntent


class QueryAnalyzer:
    """Analyzes queries to determine optimal processing strategies"""
    
    def __init__(self):
        """Initialize query analyzer"""
        self.intent_patterns = {
            QueryIntent.FACTUAL: [
                r"what is", r"who is", r"when did", r"where is", 
                r"how many", r"list", r"define", r"explain"
            ],
            QueryIntent.ANALYTICAL: [
                r"why", r"how does", r"analyze", r"compare", 
                r"evaluate", r"assess", r"relationship"
            ],
            QueryIntent.COMPARISON: [
                r"difference between", r"compare", r"versus", 
                r"vs", r"better", r"pros and cons"
            ],
            QueryIntent.CREATIVE: [
                r"write", r"create", r"generate", r"imagine", 
                r"story", r"poem", r"creative"
            ],
        }
    
    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine intent and complexity
        
        Args:
            query: User query text
        
        Returns:
            Analysis results including recommended strategies
        """
        analysis = {
            "intent": self._classify_intent(query),
            "complexity": self._assess_complexity(query),
            "keywords": self._extract_keywords(query),
            "recommended_retrieval": None,
            "recommended_reranking": None,
            "recommended_template": None,
        }
        
        # Determine recommended strategies
        analysis["recommended_retrieval"] = self._recommend_retrieval(analysis)
        analysis["recommended_reranking"] = self._recommend_reranking(analysis)
        analysis["recommended_template"] = self._recommend_template(analysis)
        
        return analysis
    
    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify query intent"""
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        return QueryIntent.FACTUAL  # Default
    
    def _assess_complexity(self, query: str) -> int:
        """Assess query complexity (1-5)"""
        complexity = 1
        
        # Multi-hop indicators
        if any(word in query.lower() for word in ["because", "therefore", "since", "due to"]):
            complexity += 1
        
        # Temporal indicators
        if any(word in query.lower() for word in ["before", "after", "during", "timeline"]):
            complexity += 1
        
        # Comparison indicators
        if any(word in query.lower() for word in ["compare", "difference", "versus", "vs"]):
            complexity += 1
        
        # Length complexity
        if len(query.split()) > 15:
            complexity += 1
        
        return min(complexity, 5)
    
    def _extract_keywords(self, query: str) -> list:
        """Extract important keywords from query"""
        # Remove stop words (simplified)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                     "have", "has", "had", "do", "does", "did", "will", "would", "could",
                     "should", "may", "might", "must", "shall", "can", "need", "dare",
                     "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
                     "into", "through", "during", "before", "after", "above", "below",
                     "between", "under", "again", "further", "then", "once"}
        
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _recommend_retrieval(self, analysis: Dict[str, Any]) -> str:
        """Recommend retrieval strategy based on analysis"""
        if analysis["intent"] == QueryIntent.ANALYTICAL:
            return "hybrid"
        elif analysis["complexity"] >= 4:
            return "mmr"
        else:
            return "similarity"
    
    def _recommend_reranking(self, analysis: Dict[str, Any]) -> str:
        """Recommend re-ranking strategy based on analysis"""
        if analysis["complexity"] >= 4:
            return "cross_encoder"
        elif analysis["intent"] in [QueryIntent.ANALYTICAL, QueryIntent.COMPARISON]:
            return "bm25"
        else:
            return None  # No re-ranking needed
    
    def _recommend_template(self, analysis: Dict[str, Any]) -> str:
        """Recommend prompt template based on intent"""
        intent_map = {
            QueryIntent.FACTUAL: "factual_qa",
            QueryIntent.ANALYTICAL: "analysis",
            QueryIntent.COMPARISON: "comparison",
            QueryIntent.CREATIVE: "creative",
        }
        return intent_map.get(analysis["intent"], "factual_qa")
