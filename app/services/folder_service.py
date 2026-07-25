"""Folder Service"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.document import Folder, FolderResponse
from datetime import datetime


class FolderService:
    """Folder management service"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize folder service
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_folder(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> FolderResponse:
        """
        Create a new folder
        
        Args:
            user_id: User ID
            name: Folder name
            description: Optional description
            color: Optional color for UI
            parent_id: Optional parent folder ID
        
        Returns:
            Created folder response
        """
        db_folder = Folder(
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            parent_id=parent_id
        )
        
        self.db.add(db_folder)
        await self.db.commit()
        await self.db.refresh(db_folder)
        
        return FolderResponse.model_validate(db_folder)
    
    async def list_folders(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[FolderResponse]:
        """List user's folders"""
        result = await self.db.execute(
            select(Folder)
            .where(Folder.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Folder.created_at.desc())
        )
        folders = result.scalars().all()
        return [FolderResponse.model_validate(folder) for folder in folders]
    
    async def get_folder(
        self,
        folder_id: str,
        user_id: str
    ) -> Optional[FolderResponse]:
        """Get a specific folder"""
        result = await self.db.execute(
            select(Folder)
            .where(Folder.id == folder_id, Folder.user_id == user_id)
        )
        folder = result.scalar_one_or_none()
        
        if folder:
            return FolderResponse.model_validate(folder)
        return None
    
    async def update_folder(
        self,
        folder_id: str,
        user_id: str,
        update_data: dict
    ) -> Optional[FolderResponse]:
        """Update folder metadata"""
        result = await self.db.execute(
            select(Folder)
            .where(Folder.id == folder_id, Folder.user_id == user_id)
        )
        folder = result.scalar_one_or_none()
        
        if not folder:
            return None
        
        for key, value in update_data.items():
            if hasattr(folder, key):
                setattr(folder, key, value)
        
        folder.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(folder)
        
        return FolderResponse.model_validate(folder)
    
    async def delete_folder(
        self,
        folder_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a folder
        
        Args:
            folder_id: Folder ID
            user_id: User ID
        
        Returns:
            True if successful
        """
        result = await self.db.execute(
            select(Folder)
            .where(Folder.id == folder_id, Folder.user_id == user_id)
        )
        folder = result.scalar_one_or_none()
        
        if not folder:
            return False
        
        # Move documents in this folder to root (set folder_id to None)
        from app.models.document import Document
        await self.db.execute(
            select(Document)
            .where(Document.folder_id == folder_id)
        )
        
        # Delete the folder
        await self.db.execute(
            delete(Folder).where(Folder.id == folder_id)
        )
        await self.db.commit()
        
        return True
