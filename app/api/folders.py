"""Folders API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.document import FolderCreate, FolderResponse, FolderUpdate
from app.services.folder_service import FolderService
from app.dependencies import get_db, get_current_user

router = APIRouter()


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new folder"""
    folder_service = FolderService(db)
    try:
        folder = await folder_service.create_folder(
            user_id=current_user.id,
            **folder_data.dict(exclude_unset=True)
        )
        return folder
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[FolderResponse])
async def list_folders(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's folders"""
    folder_service = FolderService(db)
    folders = await folder_service.list_folders(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return folders


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific folder"""
    folder_service = FolderService(db)
    folder = await folder_service.get_folder(folder_id, current_user.id)
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    return folder


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    update_data: FolderUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update folder metadata"""
    folder_service = FolderService(db)
    folder = await folder_service.update_folder(
        folder_id,
        current_user.id,
        update_data.dict(exclude_unset=True)
    )
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a folder (and optionally move documents to root)"""
    folder_service = FolderService(db)
    success = await folder_service.delete_folder(folder_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    return None
