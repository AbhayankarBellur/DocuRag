"""Qdrant Vector Storage"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from app.utils.config import settings


class QdrantStorage:
    """Qdrant Vector Storage Implementation"""
    
    def __init__(
        self,
        url: str = None,
        api_key: str = None,
        collection_name: str = "documents",
        vector_size: int = 384
    ):
        """
        Initialize Qdrant storage
        
        Args:
            url: Qdrant server URL
            api_key: Qdrant API key (if required)
            collection_name: Name of the collection
            vector_size: Dimension of the vectors
        """
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Qdrant client and collection"""
        try:
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key if self.api_key else None
            )
            
            # Create collection if it doesn't exist
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Qdrant: {e}")
    
    def add_documents(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add documents to the collection
        
        Args:
            embeddings: List of embedding vectors
            texts: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
        """
        try:
            points = []
            for i, (embedding, text, metadata, doc_id) in enumerate(
                zip(embeddings, texts, metadatas, ids)
            ):
                payload = {"text": text, **metadata}
                points.append(
                    PointStruct(
                        id=doc_id,
                        vector=embedding,
                        payload=payload
                    )
                )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            raise RuntimeError(f"Failed to add documents to Qdrant: {e}")
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the collection for similar documents
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            filter_dict: Filter conditions on metadata
        
        Returns:
            Dictionary containing query results
        """
        try:
            # Build filter if provided
            query_filter = None
            if filter_dict:
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=conditions)
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=n_results,
                query_filter=query_filter,
                with_payload=True
            )
            
            # Format results
            formatted = {
                "ids": [r.id for r in results],
                "documents": [r.payload.get("text", "") for r in results],
                "metadatas": [r.payload for r in results],
                "distances": [r.score for r in results],
                "embeddings": [r.vector for r in results]
            }
            
            return formatted
        except Exception as e:
            raise RuntimeError(f"Failed to query Qdrant: {e}")
    
    def delete(self, ids: List[str]) -> None:
        """
        Delete documents from the collection
        
        Args:
            ids: List of document IDs to delete
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
        except Exception as e:
            raise RuntimeError(f"Failed to delete documents from Qdrant: {e}")
    
    def get(self, ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get documents from the collection
        
        Args:
            ids: List of document IDs to retrieve
        
        Returns:
            Dictionary containing documents
        """
        try:
            if ids:
                results = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=ids,
                    with_payload=True,
                    with_vectors=True
                )
            else:
                # Get all documents (scroll)
                results = []
                offset = None
                while True:
                    batch = self.client.scroll(
                        collection_name=self.collection_name,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=True
                    )
                    results.extend(batch[0])
                    offset = batch[1]
                    if offset is None:
                        break
            
            formatted = {
                "ids": [r.id for r in results],
                "documents": [r.payload.get("text", "") for r in results],
                "metadatas": [r.payload for r in results],
                "embeddings": [r.vector for r in results]
            }
            
            return formatted
        except Exception as e:
            raise RuntimeError(f"Failed to get documents from Qdrant: {e}")
    
    def count(self) -> int:
        """Get the number of documents in the collection"""
        try:
            return self.client.count(collection_name=self.collection_name).count
        except Exception as e:
            raise RuntimeError(f"Failed to count documents in Qdrant: {e}")
    
    def clear(self) -> None:
        """Clear all documents from the collection"""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
        except Exception as e:
            raise RuntimeError(f"Failed to clear Qdrant collection: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        return {
            "name": self.collection_name,
            "count": self.count(),
            "storage_type": "qdrant",
            "url": self.url,
            "vector_size": self.vector_size
        }
