"""HuggingFace Inference Generation Engine"""
from typing import List, Dict, Any, Optional
import requests
import time
from app.utils.config import settings


class HFInference:
    """HuggingFace Inference API for text generation"""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        api_url: str = None
    ):
        """
        Initialize HuggingFace Inference
        
        Args:
            api_key: HuggingFace API key
            model: Model name (default: Qwen2.5-0.5B-Instruct)
            api_url: API base URL
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_model
        self.api_url = api_url or settings.hf_api_url
        
        self.offline_mode = not bool(self.api_key)
        
        self.endpoint = f"{self.api_url}/{self.model}"
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        self.request_count = 0
        self.max_requests_per_minute = 60
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
        return_full_text: bool = False
    ) -> Dict[str, Any]:
        """
        Generate text using HuggingFace Inference API
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            top_p: Nucleus sampling parameter
            do_sample: Whether to use sampling
            return_full_text: Whether to return full text including prompt
        
        Returns:
            Dictionary containing generated text and metadata
        """
        # Rate limiting
        self._rate_limit()

        if self.offline_mode:
            return {
                "generated_text": self._offline_generate(prompt),
                "model": self.model,
                "tokens_used": len(prompt.split()),
                "request_id": self.request_count + 1,
            }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": do_sample,
                "return_full_text": return_full_text
            }
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 503:
                # Model is loading, wait and retry
                time.sleep(5)
                return self.generate(prompt, max_tokens, temperature, top_p, do_sample, return_full_text)
            
            response.raise_for_status()
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list):
                generated_text = result[0].get("generated_text", "")
            else:
                generated_text = result.get("generated_text", "")
            
            self.request_count += 1
            
            return {
                "generated_text": generated_text,
                "model": self.model,
                "tokens_used": len(generated_text.split()),  # Approximate
                "request_id": self.request_count
            }
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"HuggingFace inference failed: {e}")

    def _offline_generate(self, prompt: str) -> str:
        """Simple local fallback when no Hugging Face API key is configured."""
        lower_prompt = prompt.lower()
        if "question:" in lower_prompt and "context:" in lower_prompt:
            context_start = lower_prompt.find("context:")
            question_start = lower_prompt.find("question:")
            context = prompt[context_start + len("context:"):question_start].strip()
            if context:
                sentences = [sentence.strip() for sentence in context.replace("\n", " ").split(".") if sentence.strip()]
                summary = ". ".join(sentences[:2])
                return summary if summary else context[:500]
        return prompt[:500]
    
    def generate_with_context(
        self,
        query: str,
        context: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        template: str = None
    ) -> Dict[str, Any]:
        """
        Generate answer with context (RAG-style)
        
        Args:
            query: User query
            context: Retrieved context documents
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            template: Optional prompt template
        
        Returns:
            Dictionary containing generated answer
        """
        if template:
            prompt = template.format(query=query, context=context)
        else:
            prompt = f"""Context: {context}

Question: {query}

Answer:"""
        
        result = self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        result["query"] = query
        result["context"] = context
        
        return result
    
    def generate_batch(
        self,
        prompts: List[str],
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Generate text for multiple prompts
        
        Args:
            prompts: List of input prompts
            max_tokens: Maximum tokens to generate per prompt
            temperature: Sampling temperature
        
        Returns:
            List of generation results
        """
        results = []
        for prompt in prompts:
            try:
                result = self.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "prompt": prompt
                })
        return results
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model": self.model,
            "endpoint": self.endpoint,
            "api_url": self.api_url,
            "max_requests_per_minute": self.max_requests_per_minute
        }
    
    def check_model_status(self) -> bool:
        """Check if the model is available"""
        try:
            response = requests.get(
                self.endpoint,
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
