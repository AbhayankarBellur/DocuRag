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
        title: Optional[str] = None
    ) -> DocumentResponse:
        """
        Upload and process a document
        
        Args:
            file: Uploaded file
            user_id: User ID
            title: Optional document title
        
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
            metadata=ingestion_result["metadata"],
            domain=ingestion_result["domain"],
            complexity_score=ingestion_result["complexity_score"],
            language=ingestion_result["language"]
        )
        
        self.db.add(db_document)
        await self.db.commit()
        await self.db.refresh(db_document)
        
        # Process document (chunking, embedding, storage)
        await self._process_document(db_document, ingestion_result["content"])
        
        return DocumentResponse.model_validate(db_document)
    
    async def _process_document(self, document: Document, content: str):
        """Process document: chunk, embed, and store"""
        # Select chunking strategy
        chunking_strategy = self.chunking_strategies.get("fixed")
        chunks = chunking_strategy.chunk(content)
        
        # Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_model.embed_batch(texts)
        
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
        
        self.vector_store.add_documents(embeddings, texts, metadatas, ids)
        
        # Update document record
        document.chunk_count = len(chunks)
        document.chunking_strategy = "fixed"
        document.embedding_model = settings.embedding_model
        document.vector_store = "chroma"
        document.status = DocumentStatus.COMPLETED
        document.processed_at = datetime.utcnow()
        
        await self.db.commit()
    
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
        
        # Delete from vector store
        chunk_ids = [f"{document_id}_{i}" for i in range(document.chunk_count)]
        self.vector_store.delete(chunk_ids)
        
        # Delete file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete from database
        await self.db.execute(
            delete(Document).where(Document.id == document_id)
        )
        await self.db.commit()
        
        return True
    
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
            if hasattr(document, key):
                setattr(document, key, value)
        
        await self.db.commit()
        await self.db.refresh(document)
        
        return DocumentResponse.model_validate(document)
