"""Application Configuration"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application Settings"""
    
    # Application
    app_name: str = "MicroBrain"
    app_version: str = "1.0.0"
    debug: bool = True
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./microbrain.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # HuggingFace
    huggingface_api_key: Optional[str] = "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"
    hf_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    hf_api_url: str = "https://api-inference.huggingface.co/models"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    # Cohere
    cohere_api_key: Optional[str] = None
    
    # Vector Storage
    vector_store_type: str = "chroma"
    chroma_persist_dir: str = "./Data/chroma"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    
    # Embedding Model
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # File Upload
    max_upload_size: int = 10485760  # 10MB
    allowed_extensions: str = "pdf,docx,pptx,txt,md,html"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
