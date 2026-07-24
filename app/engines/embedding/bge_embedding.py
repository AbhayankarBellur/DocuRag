"""BGE Embedding Model"""
from typing import List, Union
import hashlib
import math
from app.utils.config import settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None


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
            if SentenceTransformer is None:
                self.model = None
                return
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load BGE model: {e}")

    def _fallback_embedding(self, text: str, dimension: int = 384) -> List[float]:
        """Generate a deterministic lightweight embedding without external ML deps."""
        vector = [0.0] * dimension
        tokens = text.lower().split()

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimension
            weight = 1.0 + (digest[4] / 255.0)
            vector[index] += weight

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
    
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
            if self.model is None:
                embeddings = [self._fallback_embedding(item) for item in text]
                if is_single:
                    return embeddings[0]
                return embeddings

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
            if self.model is None:
                return [self._fallback_embedding(item) for item in texts]

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
        if self.model is None:
            return 384
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "embedding_dimension": self.get_embedding_dimension(),
            "model_type": "bge"
        }
