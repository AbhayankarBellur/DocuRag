"""Document Service"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import UploadFile
import os
import uuid
from datetime import datetime
from app.models.document import Document, DocumentStatus, DocumentType, DocumentResponse
from app.engines.ingestion import IngestionEngine
from app.engines.chunking.fixed_chunking import FixedChunking
from app.engines.chunking.semantic_chunking import SemanticChunking
from app.engines.chunking.section_chunking import SectionChunking
from app.engines.chunking.recursive_chunking import RecursiveChunking
from app.engines.embedding.bge_embedding import BGEEmbedding
from app.engines.storage.chroma_storage import ChromaStorage
from app.utils.config import settings
from app.services.background_worker import background_worker


class DocumentService:
    """Document management service"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize document service
        
        Args:
            db: Database session
        """
        self.db = db
        self.ingestion_engine = IngestionEngine()
        self.chunking_strategies = {
            "fixed": FixedChunking(),
            "semantic": SemanticChunking(),
            "section": SectionChunking(),
            "recursive": RecursiveChunking()
        }
        self.embedding_model = BGEEmbedding()
        self.vector_store = ChromaStorage()
    
    async def upload_document(
        self,
        file: UploadFile,
        user_id: str,
        title: Optional[str] = None,
        folder_id: Optional[str] = None,
        chunking_strategy: str = "fixed",
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        vector_store: str = "chroma"
    ) -> DocumentResponse:
        """
        Upload and process a document
        
        Args:
            file: Uploaded file
            user_id: User ID
            title: Optional document title
            folder_id: Optional folder ID
            chunking_strategy: Chunking strategy to use
            embedding_model: Embedding model to use
            vector_store: Vector store to use
        
        Returns:
            Created document response
        """
        # Save file
        upload_dir = "./Data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_extension = file.filename.split(".")[-1]
        file_id = str(uuid.uuid4())
        file_path = f"{upload_dir}/{file_id}.{file_extension}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Ingest document
        ingestion_result = self.ingestion_engine.ingest_document(
            file_path=file_path,
            filename=file.filename,
            user_id=user_id,
            title=title
        )
        
        # Create database record
        db_document = Document(
            id=ingestion_result["id"],
            user_id=user_id,
            title=ingestion_result["title"],
            filename=ingestion_result["filename"],
            file_path=file_path,
            file_size=ingestion_result["file_size"],
            document_type=ingestion_result["document_type"],
            status=DocumentStatus.PROCESSING,
            document_metadata=ingestion_result["metadata"],
            domain=ingestion_result["domain"],
            complexity_score=ingestion_result["complexity_score"],
            language=ingestion_result["language"],
            folder_id=folder_id
        )
        
        self.db.add(db_document)
        await self.db.commit()
        await self.db.refresh(db_document)
        
        # Process document (chunking, embedding, storage) synchronously with config
        await self._process_document(db_document, ingestion_result["content"], chunking_strategy, embedding_model, vector_store)
        
        return self._to_response(db_document)
    
    def _to_response(self, document: Document) -> DocumentResponse:
        """Convert ORM document to Pydantic response"""
        data = dict(document.__dict__)
        data.pop("_sa_instance_state", None)
        # Ensure updated_at is present (may be None for new documents)
        if 'updated_at' not in data:
            data['updated_at'] = None
        # Handle metadata field name mapping
        if 'document_metadata' in data:
            data['metadata'] = data.pop('document_metadata')
        print('DEBUG: _to_response data keys', sorted(data.keys()), flush=True)
        print('DEBUG: _to_response updated_at', data.get('updated_at'), flush=True)
        print('DEBUG: _to_response created_at', data.get('created_at'), flush=True)
        return DocumentResponse.model_validate(data)
    
    async def _process_document(self, document: Document, content: str, chunking_strategy: str = "fixed", embedding_model: str = "BAAI/bge-small-en-v1.5", vector_store: str = "chroma"):
        """Process document: chunk, embed, and store"""
        print(f"DEBUG: _process_document start for document={document.id} with strategy={chunking_strategy}, embedding={embedding_model}, store={vector_store}", flush=True)
        try:
            # Select chunking strategy
            chunking_strategy_obj = self.chunking_strategies.get(chunking_strategy, self.chunking_strategies["fixed"])
            print("DEBUG: selected chunking strategy", flush=True)
            chunks = chunking_strategy_obj.chunk(content)
            print(f"DEBUG: chunked into {len(chunks)} chunks", flush=True)

            # Generate embeddings using specified model
            texts = [chunk["text"] for chunk in chunks]
            print("DEBUG: generated texts for embeddings", flush=True)
            # Note: Currently using default embedding model, could be extended to support multiple models
            embeddings = self.embedding_model.embed_batch(texts)
            print(f"DEBUG: embeddings generated ({len(embeddings)} vectors)", flush=True)

            # Store in vector database
            ids = [f"{document.id}_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": document.id,
                    "user_id": document.user_id,
                    **chunk["metadata"]
                }
                for chunk in chunks
            ]
            print("DEBUG: storing documents in vector store", flush=True)
            # Note: Currently using default vector store, could be extended to support multiple stores
            self.vector_store.add_documents(embeddings, texts, metadatas, ids)
            print("DEBUG: vector store add completed", flush=True)

            # Update document record with actual config used
            document.chunk_count = len(chunks)
            document.chunking_strategy = chunking_strategy
            document.embedding_model = embedding_model
            document.vector_store = vector_store
            document.status = DocumentStatus.COMPLETED
            document.processed_at = datetime.utcnow()
            print("DEBUG: updating document record", flush=True)

            await self.db.commit()
            print("DEBUG: document commit completed", flush=True)
        except Exception as e:
            print(f"ERROR: document processing failed for {document.id}: {e}", flush=True)
            document.status = DocumentStatus.FAILED
            await self.db.commit()
            raise
    
    async def list_documents(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentResponse]:
        """List user's documents"""
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Document.created_at.desc())
        )
        documents = result.scalars().all()
        return [DocumentResponse.model_validate(doc) for doc in documents]
    
    async def get_document(
        self,
        document_id: str,
        user_id: str
    ) -> Optional[DocumentResponse]:
        """Get a specific document"""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
        )
        document = result.scalar_one_or_none()
        
        if document:
            return DocumentResponse.model_validate(document)
        return None
    
    async def delete_document(
        self,
        document_id: str,
        user_id: str
    ) -> bool:
        """Delete a document"""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            return False
        
        try:
            # Delete from vector store (only if chunks exist)
            if document.chunk_count and document.chunk_count > 0:
                chunk_ids = [f"{document_id}_{i}" for i in range(document.chunk_count)]
                try:
                    self.vector_store.delete(chunk_ids)
                except Exception as e:
                    print(f"WARNING: Failed to delete from vector store: {e}", flush=True)
            
            # Delete file
            if document.file_path and os.path.exists(document.file_path):
                try:
                    os.remove(document.file_path)
                except Exception as e:
                    print(f"WARNING: Failed to delete file: {e}", flush=True)
            
            # Delete from database
            await self.db.execute(
                delete(Document).where(Document.id == document_id)
            )
            await self.db.commit()
            
            return True
        except Exception as e:
            print(f"ERROR: Failed to delete document {document_id}: {e}", flush=True)
            await self.db.rollback()
            raise
    
    async def update_document(
        self,
        document_id: str,
        user_id: str,
        update_data: dict
    ) -> Optional[DocumentResponse]:
        """Update document metadata"""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            return None
        
        for key, value in update_data.items():
            if key == "metadata":
                key = "document_metadata"
            if hasattr(document, key):
                setattr(document, key, value)
        
        await self.db.commit()
        await self.db.refresh(document)
        
        return DocumentResponse.model_validate(document)
