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
    CODE_EXPLANATION = "code_explanation"
    STEP_BY_STEP = "step_by_step"
    CRITICAL_THINKING = "critical_thinking"


class ReasoningLevel(str, Enum):
    """Reasoning Levels with associated parameters"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# Reasoning level configurations
REASONING_CONFIGS = {
    ReasoningLevel.BASIC: {
        "temperature": 0.3,
        "max_tokens": 128,
        "description": "Quick, direct answers for simple questions"
    },
    ReasoningLevel.INTERMEDIATE: {
        "temperature": 0.5,
        "max_tokens": 256,
        "description": "Balanced reasoning for standard queries"
    },
    ReasoningLevel.ADVANCED: {
        "temperature": 0.7,
        "max_tokens": 512,
        "description": "Detailed analysis with step-by-step reasoning"
    },
    ReasoningLevel.EXPERT: {
        "temperature": 0.9,
        "max_tokens": 1024,
        "description": "Deep analysis with creative and comprehensive responses"
    }
}

# Model-specific configurations for optimization
MODEL_CONFIGS = {
    "Qwen/Qwen2.5-0.5B-Instruct": {
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
        "timeout": 10,
        "use_cache": True
    },
    "Qwen/Qwen2.5-1.5B-Instruct": {
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.9,
        "timeout": 15,
        "use_cache": True
    },
    "Qwen/Qwen2.5-7B-Instruct": {
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.9,
        "timeout": 20,
        "use_cache": True
    }
}


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
            PromptType.CODE_EXPLANATION: self._code_explanation_template,
            PromptType.STEP_BY_STEP: self._step_by_step_template,
            PromptType.CRITICAL_THINKING: self._critical_thinking_template,
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
    
    def _code_explanation_template(self, query: str, context: str, **kwargs) -> str:
        """Template for code explanation"""
        return f"""Context: {context}

Question: {query}

Explain the code or technical concept clearly. Break down complex ideas into understandable parts, provide examples, and explain the purpose and functionality.

Answer:"""
    
    def _step_by_step_template(self, query: str, context: str, **kwargs) -> str:
        """Template for step-by-step reasoning"""
        return f"""Context: {context}

Question: {query}

Provide a step-by-step explanation. Break down the solution into clear, logical steps. Explain your reasoning at each step.

Step-by-step Answer:"""
    
    def _critical_thinking_template(self, query: str, context: str, **kwargs) -> str:
        """Template for critical thinking"""
        return f"""Context: {context}

Question: {query}

Apply critical thinking to analyze this question. Consider multiple perspectives, identify assumptions, evaluate evidence, and provide a well-reasoned conclusion. Discuss potential limitations or alternative viewpoints.

Critical Analysis:"""
    
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
    
    def get_reasoning_config(self, reasoning_level: ReasoningLevel) -> Dict[str, Any]:
        """Get configuration for a reasoning level"""
        return REASONING_CONFIGS.get(reasoning_level, REASONING_CONFIGS[ReasoningLevel.INTERMEDIATE])
    
    def get_available_reasoning_levels(self) -> list:
        """Get available reasoning levels"""
        return list(REASONING_CONFIGS.keys())
    
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
