"""BGE Embedding Model"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from app.utils.config import settings


class BGEEmbedding:
    """BGE (BAAI General Embedding) Model"""
    
    def __init__(self, model_name: str = None, device: str = None):
        """
        Initialize BGE embedding model
        
        Args:
            model_name: BGE model name (default from settings)
            device: Device to run on (cpu/cuda)
        """
        self.model_name = model_name or settings.embedding_model
        self.device = device or settings.embedding_device
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the BGE model"""
        try:
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load BGE model: {e}")
    
    def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text(s)
        
        Args:
            text: Single text string or list of texts
        
        Returns:
            Embedding vector(s) as list(s) of floats
        """
        if self.model is None:
            self._load_model()
        
        is_single = isinstance(text, str)
        if is_single:
            text = [text]
        
        try:
            embeddings = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            
            if is_single:
                return embeddings[0].tolist()
            return embeddings.tolist()
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {e}")
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors
        """
        if self.model is None:
            self._load_model()
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=True
            )
            return embeddings.tolist()
        except Exception as e:
            raise RuntimeError(f"Failed to generate batch embeddings: {e}")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        if self.model is None:
            self._load_model()
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "embedding_dimension": self.get_embedding_dimension(),
            "model_type": "bge"
        }
