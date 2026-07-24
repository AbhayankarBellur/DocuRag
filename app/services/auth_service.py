"""Authentication Service"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole, UserCreate, UserResponse, Token
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.utils.config import settings


class AuthService:
    """Authentication and user management service"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize auth service
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user
        
        Args:
            user_data: User creation data
        
        Returns:
            Created user response
        """
        # Check if user already exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=UserRole.USER,
            is_active=True,
            is_verified=False
        )
        
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        
        return UserResponse.model_validate(db_user)
    
    async def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[UserResponse]:
        """
        Authenticate user with email and password
        
        Args:
            email: User email
            password: User password
        
        Returns:
            User response if authenticated, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            raise ValueError("User account is inactive")
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        return UserResponse.model_validate(user)
    
    async def create_tokens(
        self,
        user: UserResponse
    ) -> Token:
        """
        Create access and refresh tokens for user
        
        Args:
            user: User response
        
        Returns:
            Token pair
        """
        token_data = {
            "sub": user.email,
            "user_id": user.id,
            "role": user.role
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a token
        
        Args:
            token: JWT token
        
        Returns:
            Decoded token payload
        """
        return decode_token(token)
    
    async def refresh_access_token(self, refresh_token: str) -> Token:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            New token pair
        """
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        # Create new tokens
        token_data = {
            "sub": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "role": payload.get("role")
        }
        
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
        
        Returns:
            User response if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return UserResponse.model_validate(user)
    
    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """
        Get user by email
        
        Args:
            email: User email
        
        Returns:
            User response if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return UserResponse.model_validate(user)
    
    async def update_user(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[UserResponse]:
        """
        Update user information
        
        Args:
            user_id: User ID
            update_data: Data to update
        
        Returns:
            Updated user response
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Update allowed fields
        if "full_name" in update_data:
            user.full_name = update_data["full_name"]
        if "is_active" in update_data:
            user.is_active = update_data["is_active"]
        if "role" in update_data:
            user.role = update_data["role"]
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return UserResponse.model_validate(user)
    
    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
        
        Returns:
            True if successful
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        if not verify_password(old_password, user.hashed_password):
            raise ValueError("Incorrect password")
        
        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()
        
        return True
