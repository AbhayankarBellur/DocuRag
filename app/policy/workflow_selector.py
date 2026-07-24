"""Workflow Selector for Policy Engine"""
from typing import Dict, Any, Optional
from app.policy.document_analyzer import DocumentAnalyzer
from app.policy.query_analyzer import QueryAnalyzer


class WorkflowSelector:
    """Selects optimal workflow based on document and query analysis"""
    
    def __init__(self):
        """Initialize workflow selector"""
        self.document_analyzer = DocumentAnalyzer()
        self.query_analyzer = QueryAnalyzer()
    
    def select_workflow(
        self,
        document_content: str = None,
        document_metadata: Dict[str, Any] = None,
        query: str = None
    ) -> Dict[str, Any]:
        """
        Select optimal workflow based on analysis
        
        Args:
            document_content: Document text content (for document processing)
            document_metadata: Document metadata
            query: User query (for query processing)
        
        Returns:
            Selected workflow configuration
        """
        workflow = {
            "document_analysis": None,
            "query_analysis": None,
            "chunking_strategy": "fixed",
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "retrieval_strategy": "similarity",
            "reranking_strategy": None,
            "prompt_template": "factual_qa",
            "generation_params": {
                "max_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        # Analyze document if provided
        if document_content:
            doc_analysis = self.document_analyzer.analyze(document_content, document_metadata)
            workflow["document_analysis"] = doc_analysis
            
            # Apply document-based recommendations
            workflow["chunking_strategy"] = doc_analysis["recommended_chunking"]
            workflow["embedding_model"] = doc_analysis["recommended_embedding"]
            workflow["retrieval_strategy"] = doc_analysis["recommended_retrieval"]
        
        # Analyze query if provided
        if query:
            query_analysis = self.query_analyzer.analyze(query)
            workflow["query_analysis"] = query_analysis
            
            # Apply query-based recommendations (override document if query-specific)
            workflow["retrieval_strategy"] = query_analysis["recommended_retrieval"]
            workflow["reranking_strategy"] = query_analysis["recommended_reranking"]
            workflow["prompt_template"] = query_analysis["recommended_template"]
            
            # Adjust generation parameters based on intent
            if query_analysis["intent"] == "creative":
                workflow["generation_params"]["temperature"] = 0.9
                workflow["generation_params"]["max_tokens"] = 768
            elif query_analysis["intent"] == "factual":
                workflow["generation_params"]["temperature"] = 0.3
                workflow["generation_params"]["max_tokens"] = 256
        
        return workflow
    
    def get_workflow_summary(self, workflow: Dict[str, Any]) -> str:
        """
        Get human-readable summary of selected workflow
        
        Args:
            workflow: Workflow configuration
        
        Returns:
            Summary string
        """
        summary_parts = [
            f"Chunking: {workflow['chunking_strategy']}",
            f"Embedding: {workflow['embedding_model']}",
            f"Retrieval: {workflow['retrieval_strategy']}",
        ]
        
        if workflow["reranking_strategy"]:
            summary_parts.append(f"Reranking: {workflow['reranking_strategy']}")
        
        summary_parts.append(f"Template: {workflow['prompt_template']}")
        
        return " | ".join(summary_parts)
