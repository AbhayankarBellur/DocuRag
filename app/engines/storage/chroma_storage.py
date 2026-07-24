"""ChromaDB Vector Storage"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from app.utils.config import settings


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
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to query ChromaDB: {e}")
    
    def delete(self, ids: List[str]) -> None:
        """
        Delete documents from the collection
        
        Args:
            ids: List of document IDs to delete
        """
        try:
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
            results = self.collection.get(ids=ids, where=where)
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to get documents from ChromaDB: {e}")
    
    def count(self) -> int:
        """Get the number of documents in the collection"""
        try:
            return self.collection.count()
        except Exception as e:
            raise RuntimeError(f"Failed to count documents in ChromaDB: {e}")
    
    def clear(self) -> None:
        """Clear all documents from the collection"""
        try:
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
