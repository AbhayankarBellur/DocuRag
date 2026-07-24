"""OpenAI Embedding Model"""
from typing import List, Union
import openai
from app.utils.config import settings


class OpenAIEmbedding:
    """OpenAI Embedding Model (text-embedding-3-small/large)"""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embedding model
        
        Args:
            api_key: OpenAI API key (default from settings)
            model: OpenAI embedding model name
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        openai.api_key = self.api_key
    
    def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text(s)
        
        Args:
            text: Single text string or list of texts
        
        Returns:
            Embedding vector(s) as list(s) of floats
        """
        is_single = isinstance(text, str)
        if is_single:
            text = [text]
        
        try:
            response = openai.Embedding.create(
                input=text,
                model=self.model
            )
            
            embeddings = [item["embedding"] for item in response["data"]]
            
            if is_single:
                return embeddings[0]
            return embeddings
        except Exception as e:
            raise RuntimeError(f"Failed to generate OpenAI embeddings: {e}")
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (OpenAI handles batching)
        
        Returns:
            List of embedding vectors
        """
        # OpenAI handles batching internally
        return self.embed_text(texts)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(self.model, 1536)
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model,
            "embedding_dimension": self.get_embedding_dimension(),
            "model_type": "openai"
        }
