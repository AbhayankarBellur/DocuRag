"""Query Models"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.utils.config import settings
from app.models.base import Base


class QueryIntent(str, enum.Enum):
    """Query Intent Classification"""
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    COMPARISON = "comparison"


class QueryStatus(str, enum.Enum):
    """Query Processing Status"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Query(Base):
    """Query Model (for SQLAlchemy)"""
    
    __tablename__ = "queries"
    
    if "postgresql" in settings.database_url:
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    else:
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
        document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    
    question = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    complexity_score = Column(Integer, nullable=True)
    
    # Response data
    answer = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    citations = Column(JSON, nullable=True)
    
    # Workflow metadata
    retrieval_strategy = Column(String, nullable=True)
    reranking_strategy = Column(String, nullable=True)
    embedding_model = Column(String, nullable=True)
    generation_model = Column(String, nullable=True)
    prompt_template = Column(String, nullable=True)
    
    # Performance metrics
    retrieval_time = Column(Integer, nullable=True)  # milliseconds
    generation_time = Column(Integer, nullable=True)  # milliseconds
    total_time = Column(Integer, nullable=True)  # milliseconds
    token_usage = Column(Integer, nullable=True)
    
    # Evaluation metrics
    faithfulness_score = Column(Integer, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    user_feedback = Column(Integer, nullable=True)  # 1-5 rating
    
    status = Column(String, default=QueryStatus.PROCESSING, nullable=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Query {self.question[:50]}...>"


# Pydantic models for API
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class QueryBase(BaseModel):
    """Base Query Model"""
    question: str = Field(..., min_length=1)
    document_id: Optional[str] = None


class QueryCreate(QueryBase):
    """Query Creation Model"""
    # Strategy selection — pass None or "auto" for automatic policy-based selection,
    # or a concrete value (e.g. "hybrid") for manual override.
    retrieval_strategy: Optional[str] = None    # similarity | hybrid | mmr | auto
    reranking_strategy: Optional[str] = None    # bm25 | cross_encoder | cohere | none | auto
    prompt_template: Optional[str] = None       # factual_qa | analysis | comparison | creative | auto
    reasoning_level: Optional[str] = None       # basic | intermediate | advanced | expert
    # Embedding model to use at query time (must match the model used at ingestion
    # if you want correct similarity scores; "auto" uses the policy default).
    embedding_model: Optional[str] = None       # BAAI/bge-small-en-v1.5 | bge-base | bge-large | auto
    n_results: Optional[int] = 5               # Number of chunks to retrieve
    folder_id: Optional[str] = None            # Restrict retrieval to a specific folder


class QueryResponse(QueryBase):
    """Query Response Model"""
    id: str
    user_id: str
    intent: Optional[QueryIntent]
    complexity_score: Optional[int]
    answer: Optional[str]
    sources: Optional[List[Dict[str, Any]]]
    citations: Optional[List[Dict[str, Any]]]
    retrieval_strategy: Optional[str]
    reranking_strategy: Optional[str]
    embedding_model: Optional[str]
    generation_model: Optional[str]
    prompt_template: Optional[str]
    retrieval_time: Optional[int]
    generation_time: Optional[int]
    total_time: Optional[int]
    token_usage: Optional[int]
    faithfulness_score: Optional[int]
    relevance_score: Optional[int]
    user_feedback: Optional[int]
    status: QueryStatus
    error_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class BatchQueryCreate(BaseModel):
    """Batch Query Creation Model"""
    queries: List[QueryCreate]
    deferred: bool = False
    defer_until: Optional[datetime] = None


class BatchQueryResponse(BaseModel):
    """Batch Query Response Model"""
    task_id: str
    status: str
    total_queries: int
    completed_queries: int
    failed_queries: int
    results: Optional[List[QueryResponse]] = None
