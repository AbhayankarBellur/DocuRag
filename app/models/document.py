"""Document Models"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.utils.config import settings
from app.models.base import Base


class DocumentStatus(str, enum.Enum):
    """Document Processing Status"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    """Document Type Enum"""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    MD = "md"
    HTML = "html"


class Document(Base):
    """Document Model (for SQLAlchemy)"""
    
    __tablename__ = "documents"
    
    if "postgresql" in settings.database_url:
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    else:
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    document_type = Column(String, nullable=False)
    status = Column(String, default=DocumentStatus.UPLOADING, nullable=False)
    
    # Processing metadata
    chunk_count = Column(Integer, default=0)
    chunking_strategy = Column(String, nullable=True)
    embedding_model = Column(String, nullable=True)
    vector_store = Column(String, nullable=True)
    
    # Document analysis
    document_metadata = Column("metadata", JSON, nullable=True)
    domain = Column(String, nullable=True)
    complexity_score = Column(Integer, nullable=True)
    language = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Document {self.title}>"


# Pydantic models for API
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class DocumentBase(BaseModel):
    """Base Document Model"""
    title: str
    filename: str
    document_type: DocumentType


class DocumentCreate(DocumentBase):
    """Document Creation Model"""
    file_size: int


class DocumentResponse(DocumentBase):
    """Document Response Model"""
    id: str
    user_id: str
    status: DocumentStatus
    chunk_count: int
    chunking_strategy: Optional[str]
    embedding_model: Optional[str]
    vector_store: Optional[str]
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="document_metadata")
    domain: Optional[str]
    complexity_score: Optional[int]
    language: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    """Document Update Model"""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
