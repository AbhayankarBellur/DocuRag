"""Policy Engine Orchestrator"""
from typing import Dict, Any, Optional
from app.policy.document_analyzer import DocumentAnalyzer
from app.policy.query_analyzer import QueryAnalyzer
from app.policy.workflow_selector import WorkflowSelector


class PolicyEngine:
    """Policy Engine for dynamic workflow selection"""
    
    def __init__(self):
        """Initialize policy engine"""
        self.document_analyzer = DocumentAnalyzer()
        self.query_analyzer = QueryAnalyzer()
        self.workflow_selector = WorkflowSelector()
    
    def process_document(
        self,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process document and determine optimal strategies
        
        Args:
            content: Document content
            metadata: Document metadata
        
        Returns:
            Processing configuration
        """
        analysis = self.document_analyzer.analyze(content, metadata)
        
        return {
            "analysis": analysis,
            "workflow": self.workflow_selector.select_workflow(
                document_content=content,
                document_metadata=metadata
            )
        }
    
    def process_query(
        self,
        query: str,
        document_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process query and determine optimal strategies
        
        Args:
            query: User query
            document_analysis: Optional document analysis results
        
        Returns:
            Processing configuration
        """
        analysis = self.query_analyzer.analyze(query)
        
        return {
            "analysis": analysis,
            "workflow": self.workflow_selector.select_workflow(query=query)
        }
    
    def get_full_workflow(
        self,
        document_content: str = None,
        document_metadata: Dict[str, Any] = None,
        query: str = None
    ) -> Dict[str, Any]:
        """
        Get complete workflow for document + query processing
        
        Args:
            document_content: Document content
            document_metadata: Document metadata
            query: User query
        
        Returns:
            Complete workflow configuration
        """
        return self.workflow_selector.select_workflow(
            document_content=document_content,
            document_metadata=document_metadata,
            query=query
        )
    
    def evaluate_workflow_performance(
        self,
        workflow: Dict[str, Any],
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Evaluate workflow performance and suggest improvements
        
        Args:
            workflow: Workflow configuration used
            metrics: Performance metrics (relevance, latency, etc.)
        
        Returns:
            Evaluation results and suggestions
        """
        evaluation = {
            "workflow": workflow,
            "metrics": metrics,
            "score": self._calculate_score(metrics),
            "suggestions": []
        }
        
        # Generate suggestions based on metrics
        if metrics.get("relevance", 0) < 0.7:
            evaluation["suggestions"].append(
                "Consider using semantic chunking for better relevance"
            )
        
        if metrics.get("latency", 0) > 3000:  # 3 seconds
            evaluation["suggestions"].append(
                "Consider using smaller embedding model for faster processing"
            )
        
        if metrics.get("diversity", 0) < 0.5:
            evaluation["suggestions"].append(
                "Consider using MMR retrieval for more diverse results"
            )
        
        return evaluation
    
    def _calculate_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall workflow score"""
        weights = {
            "relevance": 0.4,
            "latency": 0.2,
            "diversity": 0.2,
            "user_satisfaction": 0.2
        }
        
        score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in metrics:
                # Normalize latency (lower is better)
                value = metrics[metric]
                if metric == "latency":
                    value = max(0, 1 - value / 5000)  # Normalize to 0-1
                score += value * weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0
