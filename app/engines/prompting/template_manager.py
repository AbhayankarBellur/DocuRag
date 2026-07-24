"""Prompt Template Manager"""
from typing import Dict, Any, Optional
from enum import Enum


class PromptType(str, Enum):
    """Prompt Template Types"""
    FACTUAL_QA = "factual_qa"
    ANALYSIS = "analysis"
    SUMMARY = "summary"
    COMPARISON = "comparison"
    CREATIVE = "creative"


class TemplateManager:
    """Manages prompt templates for different query types"""
    
    def __init__(self):
        """Initialize template manager with default templates"""
        self.templates = {
            PromptType.FACTUAL_QA: self._factual_qa_template,
            PromptType.ANALYSIS: self._analysis_template,
            PromptType.SUMMARY: self._summary_template,
            PromptType.COMPARISON: self._comparison_template,
            PromptType.CREATIVE: self._creative_template,
        }
    
    def get_template(
        self,
        prompt_type: PromptType,
        query: str,
        context: str,
        **kwargs
    ) -> str:
        """
        Get formatted prompt template
        
        Args:
            prompt_type: Type of prompt template
            query: User query
            context: Retrieved context
            **kwargs: Additional template variables
        
        Returns:
            Formatted prompt string
        """
        template_func = self.templates.get(prompt_type)
        if not template_func:
            template_func = self._factual_qa_template  # Default
        
        return template_func(query=query, context=context, **kwargs)
    
    def _factual_qa_template(self, query: str, context: str, **kwargs) -> str:
        """Template for factual question answering"""
        return f"""Context: {context}

Question: {query}

Based on the context provided, answer the question accurately and concisely. If the answer is not in the context, say so.

Answer:"""
    
    def _analysis_template(self, query: str, context: str, **kwargs) -> str:
        """Template for analytical queries"""
        return f"""Context: {context}

Question: {query}

Analyze the context to provide a detailed answer. Consider multiple perspectives and provide reasoning for your conclusions.

Answer:"""
    
    def _summary_template(self, query: str, context: str, **kwargs) -> str:
        """Template for summarization"""
        return f"""Context: {context}

Task: {query}

Provide a comprehensive summary of the context, highlighting key points and main ideas.

Summary:"""
    
    def _comparison_template(self, query: str, context: str, **kwargs) -> str:
        """Template for comparison queries"""
        return f"""Context: {context}

Question: {query}

Compare and contrast the information in the context. Highlight similarities and differences.

Answer:"""
    
    def _creative_template(self, query: str, context: str, **kwargs) -> str:
        """Template for creative content generation"""
        return f"""Context: {context}

Request: {query}

Generate creative content based on the context. Be imaginative while staying relevant to the source material.

Response:"""
    
    def add_custom_template(
        self,
        prompt_type: str,
        template_func: callable
    ) -> None:
        """
        Add a custom prompt template
        
        Args:
            prompt_type: Name/identifier for the template
            template_func: Function that returns formatted prompt
        """
        self.templates[prompt_type] = template_func
    
    def get_template_types(self) -> list:
        """Get available template types"""
        return list(self.templates.keys())
    
    def format_prompt(
        self,
        template_str: str,
        query: str,
        context: str,
        **kwargs
    ) -> str:
        """
        Format a custom template string
        
        Args:
            template_str: Template string with placeholders
            query: User query
            context: Retrieved context
            **kwargs: Additional template variables
        
        Returns:
            Formatted prompt string
        """
        try:
            return template_str.format(
                query=query,
                context=context,
                **kwargs
            )
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")
