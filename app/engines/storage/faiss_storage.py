"""FAISS Vector Storage"""
from typing import List, Dict, Any, Optional
import faiss
import numpy as np
import pickle
import os
from app.utils.config import settings


class FAISSStorage:
    """FAISS Vector Storage Implementation"""
    
    def __init__(
        self,
        index_path: str = "./Data/faiss_index",
        vector_size: int = 384,
        index_type: str = "IndexFlatIP"
    ):
        """
        Initialize FAISS storage
        
        Args:
            index_path: Path to save/load the FAISS index
            vector_size: Dimension of the vectors
            index_type: Type of FAISS index (IndexFlatIP, IndexIVFFlat, etc.)
        """
        self.index_path = index_path
        self.vector_size = vector_size
        self.index_type = index_type
        self.index = None
        self.documents = {}  # Map index to document data
        self._initialize()
    
    def _initialize(self):
        """Initialize FAISS index"""
        try:
            # Try to load existing index
            if os.path.exists(self.index_path):
                self._load_index()
            else:
                # Create new index
                if self.index_type == "IndexFlatIP":
                    self.index = faiss.IndexFlatIP(self.vector_size)
                elif self.index_type == "IndexFlatL2":
                    self.index = faiss.IndexFlatL2(self.vector_size)
                elif self.index_type == "IndexIVFFlat":
                    quantizer = faiss.IndexFlatIP(self.vector_size)
                    self.index = faiss.IndexIVFFlat(quantizer, self.vector_size, 100)
                else:
                    self.index = faiss.IndexFlatIP(self.vector_size)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize FAISS: {e}")
    
    def _save_index(self):
        """Save the FAISS index and documents to disk"""
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            
            # Save index
            faiss.write_index(self.index, self.index_path)
            
            # Save documents
            docs_path = self.index_path.replace(".index", "_documents.pkl")
            with open(docs_path, "wb") as f:
                pickle.dump(self.documents, f)
        except Exception as e:
            raise RuntimeError(f"Failed to save FAISS index: {e}")
    
    def _load_index(self):
        """Load the FAISS index and documents from disk"""
        try:
            # Load index
            self.index = faiss.read_index(self.index_path)
            
            # Load documents
            docs_path = self.index_path.replace(".index", "_documents.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, "rb") as f:
                    self.documents = pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load FAISS index: {e}")
    
    def add_documents(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add documents to the index
        
        Args:
            embeddings: List of embedding vectors
            texts: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
        """
        try:
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings_array)
            
            # Add to index
            start_idx = self.index.ntotal
            self.index.add(embeddings_array)
            
            # Store document data
            for i, (text, metadata, doc_id) in enumerate(zip(texts, metadatas, ids)):
                self.documents[start_idx + i] = {
                    "id": doc_id,
                    "text": text,
                    "metadata": metadata
                }
            
            # Save to disk
            self._save_index()
        except Exception as e:
            raise RuntimeError(f"Failed to add documents to FAISS: {e}")
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 10
    ) -> Dict[str, Any]:
        """
        Query the index for similar documents
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
        
        Returns:
            Dictionary containing query results
        """
        try:
            # Convert to numpy array and normalize
            query_array = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_array)
            
            # Search
            distances, indices = self.index.search(query_array, n_results)
            
            # Format results
            results = {
                "ids": [],
                "documents": [],
                "metadatas": [],
                "distances": [],
                "embeddings": []
            }
            
            for i, idx in enumerate(indices[0]):
                if idx in self.documents:
                    doc = self.documents[idx]
                    results["ids"].append(doc["id"])
                    results["documents"].append(doc["text"])
                    results["metadatas"].append(doc["metadata"])
                    results["distances"].append(float(distances[0][i]))
            
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to query FAISS: {e}")
    
    def delete(self, ids: List[str]) -> None:
        """
        Delete documents from the index
        Note: FAISS doesn't support efficient deletion, so we rebuild the index
        
        Args:
            ids: List of document IDs to delete
        """
        try:
            # Find indices to keep
            ids_to_remove = set(ids)
            new_documents = {}
            new_embeddings = []
            new_texts = []
            new_metadatas = []
            new_doc_ids = []
            
            for idx, doc in self.documents.items():
                if doc["id"] not in ids_to_remove:
                    new_documents[idx] = doc
                    # Note: We'd need to store embeddings to rebuild
                    # For simplicity, we'll just mark as deleted in metadata
            
            # Mark as deleted
            for idx, doc in self.documents.items():
                if doc["id"] in ids_to_remove:
                    doc["metadata"]["deleted"] = True
            
            self._save_index()
        except Exception as e:
            raise RuntimeError(f"Failed to delete documents from FAISS: {e}")
    
    def get(self, ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get documents from the index
        
        Args:
            ids: List of document IDs to retrieve
        
        Returns:
            Dictionary containing documents
        """
        try:
            results = {
                "ids": [],
                "documents": [],
                "metadatas": []
            }
            
            if ids:
                ids_set = set(ids)
                for doc in self.documents.values():
                    if doc["id"] in ids_set and not doc["metadata"].get("deleted", False):
                        results["ids"].append(doc["id"])
                        results["documents"].append(doc["text"])
                        results["metadatas"].append(doc["metadata"])
            else:
                for doc in self.documents.values():
                    if not doc["metadata"].get("deleted", False):
                        results["ids"].append(doc["id"])
                        results["documents"].append(doc["text"])
                        results["metadatas"].append(doc["metadata"])
            
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to get documents from FAISS: {e}")
    
    def count(self) -> int:
        """Get the number of documents in the index"""
        try:
            return sum(
                1 for doc in self.documents.values()
                if not doc["metadata"].get("deleted", False)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to count documents in FAISS: {e}")
    
    def clear(self) -> None:
        """Clear all documents from the index"""
        try:
            self.index = faiss.IndexFlatIP(self.vector_size)
            self.documents = {}
            self._save_index()
        except Exception as e:
            raise RuntimeError(f"Failed to clear FAISS index: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        return {
            "name": "faiss_index",
            "count": self.count(),
            "storage_type": "faiss",
            "index_path": self.index_path,
            "vector_size": self.vector_size,
            "index_type": self.index_type
        }
