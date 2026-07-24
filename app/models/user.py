"""User Models"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.utils.config import settings


class UserRole(str, enum.Enum):
    """User Role Enum"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User:
    """User Model (for SQLAlchemy)"""
    
    __tablename__ = "users"
    
    if "postgresql" in settings.database_url:
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    else:
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User {self.email}>"


# Pydantic models for API
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserBase(BaseModel):
    """Base User Model"""
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """User Creation Model"""
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User Login Model"""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """User Response Model"""
    id: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token Response Model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token Data Model"""
    email: str | None = None
    user_id: str | None = None
