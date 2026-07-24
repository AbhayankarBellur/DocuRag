"""ChromaDB Vector Storage"""
from typing import List, Dict, Any, Optional
import math
import os
from app.utils.config import settings

try:
    import chromadb
    from chromadb.config import Settings
except Exception:  # pragma: no cover - optional dependency
    chromadb = None
    Settings = None


class ChromaStorage:
    """ChromaDB Vector Storage Implementation"""
    
    def __init__(self, persist_directory: str = None, collection_name: str = "documents"):
        """
        Initialize ChromaDB storage
        
        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory or settings.chroma_persist_dir
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            if chromadb is None:
                self.client = None
                self.collection = {
                    "ids": [],
                    "documents": [],
                    "metadatas": [],
                    "embeddings": [],
                }
                return

            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChromaDB: {e}")
    
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
            if self.client is None:
                for embedding, text, metadata, doc_id in zip(embeddings, texts, metadatas, ids):
                    self.collection["ids"].append(doc_id)
                    self.collection["documents"].append(text)
                    self.collection["metadatas"].append(metadata)
                    self.collection["embeddings"].append(list(embedding))
                return

            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            raise RuntimeError(f"Failed to add documents to ChromaDB: {e}")
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the collection for similar documents
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Filter conditions on metadata
            where_document: Filter conditions on document content
        
        Returns:
            Dictionary containing query results
        """
        try:
            if self.client is None:
                return self._fallback_query(query_embedding, n_results, where)

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to query ChromaDB: {e}")

    def _fallback_query(self, query_embedding: List[float], n_results: int, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Pure Python cosine-similarity search when ChromaDB is unavailable."""
        candidates = []

        for index, doc_id in enumerate(self.collection["ids"]):
            metadata = self.collection["metadatas"][index]
            if where:
                if any(metadata.get(key) != value for key, value in where.items()):
                    continue

            embedding = self.collection["embeddings"][index]
            score = self._cosine_similarity(query_embedding, embedding)
            candidates.append((score, index))

        candidates.sort(key=lambda item: item[0], reverse=True)
        top_candidates = candidates[:n_results]

        return {
            "ids": [[self.collection["ids"][index] for _, index in top_candidates]],
            "documents": [[self.collection["documents"][index] for _, index in top_candidates]],
            "metadatas": [[self.collection["metadatas"][index] for _, index in top_candidates]],
            "distances": [[1.0 - score for score, _ in top_candidates]],
        }

    def _cosine_similarity(self, left: List[float], right: List[float]) -> float:
        denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
        if denominator == 0:
            return 0.0
        return sum(a * b for a, b in zip(left, right)) / denominator
    
    def delete(self, ids: List[str]) -> None:
        """
        Delete documents from the collection
        
        Args:
            ids: List of document IDs to delete
        """
        try:
            if self.client is None:
                retained = [
                    i for i, doc_id in enumerate(self.collection["ids"])
                    if doc_id not in ids
                ]
                self.collection["ids"] = [self.collection["ids"][i] for i in retained]
                self.collection["documents"] = [self.collection["documents"][i] for i in retained]
                self.collection["metadatas"] = [self.collection["metadatas"][i] for i in retained]
                self.collection["embeddings"] = [self.collection["embeddings"][i] for i in retained]
                return

            self.collection.delete(ids=ids)
        except Exception as e:
            raise RuntimeError(f"Failed to delete documents from ChromaDB: {e}")
    
    def get(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get documents from the collection
        
        Args:
            ids: List of document IDs to retrieve
            where: Filter conditions on metadata
        
        Returns:
            Dictionary containing documents
        """
        try:
            if self.client is None:
                return {
                    "ids": [self.collection["ids"]],
                    "documents": [self.collection["documents"]],
                    "metadatas": [self.collection["metadatas"]],
                    "embeddings": [self.collection["embeddings"]],
                }

            results = self.collection.get(ids=ids, where=where)
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to get documents from ChromaDB: {e}")
    
    def count(self) -> int:
        """Get the number of documents in the collection"""
        try:
            if self.client is None:
                return len(self.collection["ids"])
            return self.collection.count()
        except Exception as e:
            raise RuntimeError(f"Failed to count documents in ChromaDB: {e}")
    
    def clear(self) -> None:
        """Clear all documents from the collection"""
        try:
            if self.client is None:
                self.collection = {
                    "ids": [],
                    "documents": [],
                    "metadatas": [],
                    "embeddings": [],
                }
                return

            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            raise RuntimeError(f"Failed to clear ChromaDB collection: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        return {
            "name": self.collection_name,
            "count": self.count(),
            "storage_type": "chroma",
            "persist_directory": self.persist_directory
        }
