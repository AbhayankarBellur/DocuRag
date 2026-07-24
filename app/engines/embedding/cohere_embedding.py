"""Cohere Embedding Model"""
from typing import List, Union
import cohere
from app.utils.config import settings


class CohereEmbedding:
    """Cohere Embedding Model (embed-v3)"""
    
    def __init__(self, api_key: str = None, model: str = "embed-english-v3.0"):
        """
        Initialize Cohere embedding model
        
        Args:
            api_key: Cohere API key (default from settings)
            model: Cohere embedding model name
        """
        self.api_key = api_key or settings.cohere_api_key
        self.model = model
        
        if not self.api_key:
            raise ValueError("Cohere API key is required")
        
        self.client = cohere.Client(self.api_key)
    
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
            response = self.client.embed(
                texts=text,
                model=self.model,
                input_type="search_document"
            )
            
            embeddings = response.embeddings
            
            if is_single:
                return embeddings[0]
            return embeddings
        except Exception as e:
            raise RuntimeError(f"Failed to generate Cohere embeddings: {e}")
    
    def embed_batch(self, texts: List[str], batch_size: int = 96) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (Cohere max is 96)
        
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.embed_text(batch)
            all_embeddings.extend(embeddings if isinstance(embeddings, list) else [embeddings])
        
        return all_embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        dimensions = {
            "embed-english-v3.0": 1024,
            "embed-english-light-v3.0": 384,
            "embed-multilingual-v3.0": 1024,
            "embed-multilingual-light-v3.0": 384,
        }
        return dimensions.get(self.model, 1024)
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model,
            "embedding_dimension": self.get_embedding_dimension(),
            "model_type": "cohere"
        }
