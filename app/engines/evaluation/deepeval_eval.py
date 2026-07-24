"""DeepEval Evaluation Framework"""
from typing import List, Dict, Any
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualRelevancyMetric
)
from deepeval.test_case import LLMTestCase


class DeepEvalEvaluation:
    """DeepEval-based evaluation for RAG systems"""
    
    def __init__(self, openai_api_key: str = None):
        """
        Initialize DeepEval evaluator
        
        Args:
            openai_api_key: OpenAI API key for evaluation
        """
        self.openai_api_key = openai_api_key
        self.metrics = [
            FaithfulnessMetric(threshold=0.7),
            AnswerRelevancyMetric(threshold=0.7),
            ContextualRelevancyMetric(threshold=0.7)
        ]
    
    def evaluate(
        self,
        queries: List[str],
        answers: List[str],
        contexts: List[List[str]],
        retrieval_context: List[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate RAG system using DeepEval metrics
        
        Args:
            queries: List of queries
            answers: List of generated answers
            contexts: List of retrieved contexts for each query
            retrieval_context: Optional retrieval contexts
        
        Returns:
            Evaluation results with scores
        """
        test_cases = []
        
        for i, query in enumerate(queries):
            test_case = LLMTestCase(
                input=query,
                actual_output=answers[i],
                retrieval_context=contexts[i] if retrieval_context is None else retrieval_context[i]
            )
            test_cases.append(test_case)
        
        try:
            # Run evaluation
            results = evaluate(
                test_cases=test_cases,
                metrics=self.metrics
            )
            
            # Aggregate results
            aggregated = self._aggregate_results(results)
            
            return aggregated
            
        except Exception as e:
            raise RuntimeError(f"DeepEval evaluation failed: {e}")
    
    def evaluate_single(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        retrieval_context: List[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single query-response pair
        
        Args:
            query: Query text
            answer: Generated answer
            contexts: Retrieved contexts
            retrieval_context: Optional retrieval contexts
        
        Returns:
            Evaluation results
        """
        return self.evaluate(
            queries=[query],
            answers=[answer],
            contexts=[contexts],
            retrieval_context=[retrieval_context] if retrieval_context else None
        )
    
    def _aggregate_results(self, results) -> Dict[str, Any]:
        """Aggregate evaluation results"""
        aggregated = {
            "faithfulness": [],
            "answer_relevancy": [],
            "contextual_relevancy": []
        }
        
        for result in results:
            for metric in result.metrics_data:
                if metric.name == "Faithfulness":
                    aggregated["faithfulness"].append(metric.score)
                elif metric.name == "Answer Relevancy":
                    aggregated["answer_relevancy"].append(metric.score)
                elif metric.name == "Contextual Relevancy":
                    aggregated["contextual_relevancy"].append(metric.score)
        
        # Calculate averages
        return {
            "faithfulness": sum(aggregated["faithfulness"]) / len(aggregated["faithfulness"]) if aggregated["faithfulness"] else 0,
            "answer_relevancy": sum(aggregated["answer_relevancy"]) / len(aggregated["answer_relevancy"]) if aggregated["answer_relevancy"] else 0,
            "contextual_relevancy": sum(aggregated["contextual_relevancy"]) / len(aggregated["contextual_relevancy"]) if aggregated["contextual_relevancy"] else 0,
            "overall_score": self._calculate_overall_score(aggregated)
        }
    
    def _calculate_overall_score(self, aggregated: Dict[str, float]) -> float:
        """Calculate overall score"""
        scores = [
            aggregated["faithfulness"],
            aggregated["answer_relevancy"],
            aggregated["contextual_relevancy"]
        ]
        return sum(scores) / len(scores)
    
    def get_evaluation_info(self) -> Dict[str, Any]:
        """Get evaluator information"""
        return {
            "framework": "deepeval",
            "metrics": [m.name for m in self.metrics],
            "description": "DeepEval evaluation framework for RAG systems"
        }
