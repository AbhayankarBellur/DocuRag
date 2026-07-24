"""Policy Engine Tests"""
import pytest
from app.policy.document_analyzer import DocumentAnalyzer
from app.policy.query_analyzer import QueryAnalyzer


def test_document_analyzer():
    """Test document analysis"""
    analyzer = DocumentAnalyzer()
    content = "This is a legal contract about property rights and regulations."
    
    analysis = analyzer.analyze(content)
    
    assert "domain" in analysis
    assert "complexity" in analysis
    assert "recommended_chunking" in analysis
    assert "recommended_embedding" in analysis
    assert "recommended_retrieval" in analysis


def test_query_analyzer():
    """Test query analysis"""
    analyzer = QueryAnalyzer()
    query = "What is the difference between API and REST?"
    
    analysis = analyzer.analyze(query)
    
    assert "intent" in analysis
    assert "complexity" in analysis
    assert "keywords" in analysis
    assert "recommended_retrieval" in analysis
    assert "recommended_template" in analysis


def test_domain_classification():
    """Test domain classification"""
    analyzer = DocumentAnalyzer()
    
    legal_text = "This contract is governed by the laws of the state."
    tech_text = "The API endpoint returns JSON data with status codes."
    
    legal_analysis = analyzer.analyze(legal_text)
    tech_analysis = analyzer.analyze(tech_text)
    
    assert legal_analysis["domain"] == "legal"
    assert tech_analysis["domain"] == "technical"


def test_intent_classification():
    """Test intent classification"""
    analyzer = QueryAnalyzer()
    
    factual_query = "What is the capital of France?"
    comparison_query = "Compare Python and JavaScript."
    
    factual_analysis = analyzer.analyze(factual_query)
    comparison_analysis = analyzer.analyze(comparison_query)
    
    assert factual_analysis["intent"] == "factual"
    assert comparison_analysis["intent"] == "comparison"
