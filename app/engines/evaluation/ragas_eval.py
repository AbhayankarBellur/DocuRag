"""RAGAS Evaluation Framework"""
from typing import List, Dict, Any
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset


class RAGASEvaluation:
    """RAGAS-based evaluation for RAG systems"""
    
    def __init__(self):
        """Initialize RAGAS evaluator"""
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]
    
    def evaluate(
        self,
        queries: List[str],
        answers: List[str],
        contexts: List[List[str]],
        ground_truths: List[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate RAG system using RAGAS metrics
        
        Args:
            queries: List of queries
            answers: List of generated answers
            contexts: List of retrieved contexts for each query
            ground_truths: Optional list of ground truth answers
        
        Returns:
            Evaluation results with scores
        """
        # Prepare dataset
        data = {
            "question": queries,
            "answer": answers,
            "contexts": contexts
        }
        
        if ground_truths:
            data["ground_truth"] = ground_truths
        
        dataset = Dataset.from_dict(data)
        
        try:
            # Run evaluation
            results = evaluate(
                dataset=dataset,
                metrics=self.metrics
            )
            
            # Convert to dictionary
            return {
                "faithfulness": results["faithfulness"],
                "answer_relevancy": results["answer_relevancy"],
                "context_precision": results["context_precision"],
                "context_recall": results["context_recall"] if ground_truths else None,
                "overall_score": self._calculate_overall_score(results)
            }
            
        except Exception as e:
            raise RuntimeError(f"RAGAS evaluation failed: {e}")
    
    def evaluate_single(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: str = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single query-response pair
        
        Args:
            query: Query text
            answer: Generated answer
            contexts: Retrieved contexts
            ground_truth: Optional ground truth answer
        
        Returns:
            Evaluation results
        """
        return self.evaluate(
            queries=[query],
            answers=[answer],
            contexts=[contexts],
            ground_truths=[ground_truth] if ground_truth else None
        )
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall score from individual metrics"""
        scores = [
            results["faithfulness"],
            results["answer_relevancy"],
            results["context_precision"]
        ]
        
        if "context_recall" in results and results["context_recall"] is not None:
            scores.append(results["context_recall"])
        
        return sum(scores) / len(scores) if scores else 0
    
    def get_evaluation_info(self) -> Dict[str, Any]:
        """Get evaluator information"""
        return {
            "framework": "ragas",
            "metrics": [m.name for m in self.metrics],
            "description": "RAGAS evaluation framework for RAG systems"
        }
